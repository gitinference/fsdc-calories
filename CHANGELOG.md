## [0.12.0] - 2026-07-21

### 🚀 Features

- *(data_process.py)* Add `gen_graphs_nuti_data_fiscal` method to generate fiscal year-based nutritional intake charts
## [0.11.0] - 2026-07-21

### 🐛 Bug Fixes

- *(data_process.py)* Fix net_qty calculation and add tooltips for better user experience
## [0.10.2] - 2026-07-20

### 🐛 Bug Fixes

- *(data_process.py)* Correct agriculture filter parameter in process_price method to False
## [0.10.1] - 2026-07-15

### 🐛 Bug Fixes

- *(data_process.py)* Remove ECDF filtering as it is not necessary and can be computationally expensive
- *(scratch.ipynb)* Refactor code to improve readability and maintainability by using more descriptive variable names and comments
## [0.9.1] - 2026-07-15

### 🚜 Refactor

- *(data_process.py)* Standardize nutritional inputs to kilograms and rename columns accordingly
## [0.8.0] - 2026-06-25

### 🚀 Features

- *(devenv)* Add devenv configuration files for better project management and development experience
- *(.forgejo/workflows/publish.yaml)* Add CI & Publish workflow for uv using ForgeJo and uv CLI

### 💼 Other

- Fix price rankings (#24)
