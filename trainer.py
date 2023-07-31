import os
from tqdm import tqdm

import torch
from torch.utils.data import DataLoader
from torch.cuda.amp import autocast, GradScaler
from transformers import get_cosine_schedule_with_warmup, get_linear_schedule_with_warmup, AdamW

from utils import metric_fn, print_log
from dataset import LongFinBERTDataset, Collator
from model import Model

class Trainer(object):
    def __init__(
        self,
        cfg
    ):
        self.cfg = cfg
        
    def _prepare_dataloader(self):
        print_log(self.cfg, 'Preparing the dataloaders...')
        dataset = LongFinBERTDataset(self.cfg, mode = 'train')
        eval_dataset = LongFinBERTDataset(self.cfg, mode = 'valid')
        dataloader = DataLoader(dataset, batch_size = self.cfg.batch_size, num_workers = self.cfg.num_workers, shuffle = True, collate_fn = Collator(self.cfg))
        eval_dataloader = DataLoader(dataset, batch_size = 2 * self.cfg.batch_size, num_workers = self.cfg.num_workers, shuffle = False, collate_fn = Collator(self.cfg))
        return dataloader, eval_dataloader

    def _prepare_model(self):
        print_log(self.cfg, 'Preparing the model...')
        return Model(self.cfg).to(self.cfg.device)

    def _prepare_optimizer(self, model):
        return AdamW(model.parameters(), lr = self.cfg.lr, eps = self.cfg.eps, betas = self.cfg.betas)

    def _prepare_scheduler(self, optimizer, num_train_steps):
        if self.cfg.scheduler_type == 'linear':
            scheduler = get_linear_schedule_with_warmup(
                optimizer, num_warmup_steps = self.cfg.num_warmup_steps, num_training_steps = num_train_steps
            )
        elif self.cfg.scheduler_type == 'cosine':
            scheduler = get_cosine_schedule_with_warmup(
                optimizer, num_warmup_steps = self.cfg.num_warmup_steps, num_training_steps = num_train_steps,
                num_cycles = self.cfg.num_cycles
            )
        return scheduler
    
    def _prepare_train_materials(self):
        print_log(self.cfg, 'Preparing training materials...')
        model = self._prepare_model()
        dataloader, eval_dataloader = self._prepare_dataloader()
        num_train_steps = len(dataloader) * self.cfg.nepochs
        optimizer = self._prepare_optimizer(model)
        scheduler = self._prepare_scheduler(optimizer, num_train_steps)
        return model, dataloader, optimizer, scheduler, eval_dataloader
    
    def train_each_epoch(self, model, dataloader, optimizer, scheduler):
        # Set up mix-precision training
        scaler = GradScaler(enabled = self.cfg.apex)

        loss = 0
        total_samples = 0
        global_step = 0

        if self.cfg.use_tqdm:
            tbar = tqdm(dataloader)
        else:
            tbar = dataloader

        for i, batch in enumerate(tbar):
            model.train()
            batch = {k: v.to(self.cfg.device) for k, v in batch.items()}
            with autocast(enabled = self.cfg.apex):
                batch_loss, _ = model(input_ids = batch['input_ids'], attention_mask = batch['attention_mask'], labels = batch['labels'])
            batch_size = batch['input_ids'].shape[0]
            
            # Backward
            scaler.scale(batch_loss).backward()

            # Update loss
            loss += batch_loss.item() * batch_size
            total_samples += batch_size
            
            if self.cfg.use_tqdm:
                tbar.set_postfix({'Average Loss': loss / total_samples})
            
            # Update parameters
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            optimizer.zero_grad()
            global_step += 1
        
        torch.cuda.empty_cache()
        
        return loss / total_samples
        
    def valid_each_epoch(self, model, dataloader):
        model.eval()
        
        loss = 0
        total_samples = 0
        
        for i, batch in enumerate(tbar):
            model.train()
            batch = {k: v.to(self.cfg.device) for k, v in batch.items()}
            with torch.no_grad():
                with autocast(enabled = self.cfg.apex):
                    batch_loss, _ = model(input_ids = batch['input_ids'], attention_mask = batch['attention_mask'], labels = batch['labels'])
                batch_size = batch['input_ids'].shape[0]
                
            # Update loss
            loss += batch_loss.item() * batch_size
            total_samples += batch_size
            
        return loss / total_samples
        
    def fit(self):
        # Prepare materials
        model, dataloader, optimizer, scheduler, eval_dataloader = self._prepare_train_materials()
        
        # Train
        for epoch in range(self.cfg.nepochs):
            train_loss = self.train_each_epoch(model, dataloader, optimizer, scheduler)
            valid_loss = self.valid_each_epoch(model, eval_dataloader)
            
            print_log(self.cfg,
                      'Epoch: [{0}] - '
                      'Train/Valid Loss: {train_loss:.4f}/{valid_loss:.4f}'
                      .format(epoch + 1, i + 1, len(dataloader),
                              train_loss = train_loss,
                              valid_loss = valid_loss))
            
            # Save checkpoint
            print_log(self.cfg, f'Saving the model to {self.cfg.output_dir}')
            model.backbone.save_pretrained(self.cfg.output_dir)
            self.cfg.tokenizer.save_pretrained(self.cfg.output_dir)
