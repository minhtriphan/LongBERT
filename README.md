# LongFinBERT
This is the implementation of the BERT model using the LongNet structure (paper: https://arxiv.org/pdf/2307.02486.pdf). The model is pre-trained with 10-K/Q filings of US firms from 1994 to 2018.

# For references
* Training is currently implemented on one A100 80GB;
* Maximum sequence length is 45_000 tokens;
* Training time: ~13.5 hours per epoch;
* Validating time: ~3.75 hours per epoch;
* The tokenizer was pre-trained with all data with the BERTTokenizer

# Some remarks
* The data used is in the Huggingface `datasets` format (arrow format, generated by the `save_to_disk()` method);
* The train data is split into 2 parts, whether or not using both parts to train the model is controlled by argument `--train_one_part`;
* The current model only supports an equally weighted average of the segment outputs;
* The current model does not output the attention due to high memory utilization;
* _(updating)_

# Instructions to train the model
1. Clone the repo and change the directory
```
git clone https://github.com/minhtriphan/LongFinBERT-base.git
cd LongBERT
```
or
```
!git clone https://github.com/minhtriphan/LongFinBERT-base.git
import sys
sys.path.append('/LongFinBERT-base')
```

2. Download the datasets
```
kaggle datasets download -d shinomoriaoshi/10-x-filings-train-part-1
kaggle datasets download -d shinomoriaoshi/10x-filings-train-part-2
kaggle datasets download -d shinomoriaoshi/10x-filings-valid
mkdir data
mkdir data/train
unzip 10-x-filings-train-part-1.zip -d data/train/train_part_1
unzip 10x-filings-train-part-2.zip -d data/train/train_part_2
unzip 10x-filings-valid.zip -d data/valid
```
If you want to run the debugging mode with the dummy training and validation data, please download the dummy dataset here `kaggle datasets download -d shinomoriaoshi/10-x-filings-dummy-datasets`

3. Install requirements
```
pip install -r requirement.txt
```
_(In some cases with entirely new environments, some more packages are required to be installed)_

4. Run
```
python main.py \
    --seed 1 \
    --ver v1a \
    --device cuda:0 \
    --debug 0 \
    --use_log 1 \
    --use_tqdm 1 \
    --backbone ./tokenizer \
    --max_len 45_000 \
    --nepochs 5 \
    --batch_size 2 \
    --gradient_accumulation_steps 4 \
    --train_one_part 0 \
    --train_data_dir /data/train \
    --valid_data_dir /data/valid
```

# Description of the arguments
```
# General settings
parser.add_argument('--seed', type = int, default = 1, help = 'The random state.')
parser.add_argument('--ver', type = str, default = 'v1a', help = 'The name of the current version.')
parser.add_argument('--use_log', type = int, default = 0, help = 'Whether we log the training process or not, only takes 0 or 1.')
parser.add_argument('--use_tqdm', type = int, default = 0, help = 'Whether we use loop tracking or not, only takes 0 or 1.')
parser.add_argument('--debug', type = int, default = 0, help = 'Whether in the debugging mode or not.')
parser.add_argument('--device', type = str, default = 'cpu', help = 'The training device.')
    
# Model
parser.add_argument('--backbone', type = str, default = '.', help = 'The checkpoint of the tokenizer.')
    
# Data
parser.add_argument('--max_len', type = int, default = 10_000, help = 'The maximum sequence length.')
    
# Training
parser.add_argument('--train_one_part', type = int, default = 1, help = 'Whether or not training only the first part, or both parts of the training data.')
parser.add_argument('--gradient_accumulation_steps', type = int, default = 1, help = 'The number of gradient accumulation steps.')
parser.add_argument('--apex', type = int, default = 1, help = 'Whether or not we train with mixed precision.')
parser.add_argument('--nepochs', type = int, default = 5, help = 'The number of training epochs.')
parser.add_argument('--batch_size', type = int, default = 4, help = 'The batch size.')
    
# Optimizer
parser.add_argument('--lr', type = float, default = 2e-5, help = 'The training learning rate.')
parser.add_argument('--weight_decay', type = float, default = 1e-2, help = 'The coefficient for L2-regularization.')
parser.add_argument('--min_lr', type = float, default = 1e-6, help = 'The minimum training learning rate.')
    
# Schduler
parser.add_argument('--scheduler_type', type = str, default = 'cosine', help = 'The type of the scheduler.')
parser.add_argument('--num_warmup_steps', type = float, default = 0., help = 'The proportion of warm-up steps.')
    
# Paths
parser.add_argument('--train_data_dir', type = str, default = '.', help = 'The training data directory.')
parser.add_argument('--valid_data_dir', type = str, default = '.', help = 'The validating data directory.')
parser.add_argument('--test_data_dir', type = str, default = '.', help = 'The testing data directory.')
```
