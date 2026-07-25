# Food Intelligence System USA

This project builds a food image dataset for dish recognition and downstream nutrition and sustainability analysis for USA. The pipeline now includes a high-resolution image collection step and an interactive validation step for reviewing auto-labeled images.

## Project Overview

The system is designed to:
- collect food images from Bing Images for a large set of U.S. restaurant dishes
- save them into a structured dataset directory
- validate image labels manually to assess auto-label quality
- support future modeling and nutrition-aware analysis workflows

## Dataset Collection

The image collection script is implemented in [bing_image_scraper_hd.py](bing_image_scraper_hd.py).

### What changed
- The scraper now downloads high-resolution images and filters them by minimum dimensions before saving.
- Images are stored under a dedicated dataset folder named [USA_Food_Collection](USA_Food_Collection).
- Each dish is saved in its own subfolder, with filenames such as:
  - Apple_Pie_1.jpg
  - Cheeseburger_2.jpg
  - Chicken_Nuggets_10.jpg

### Dataset structure

```text
USA_Food_Collection/
├── Apple Pie/
│   ├── Apple_Pie_1.jpg
│   ├── Apple_Pie_2.jpg
│   └── ...
├── Cheeseburger/
│   ├── Cheeseburger_1.jpg
│   └── ...
└── ...
```

### How to run collection

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Make sure Chrome is installed and available in your environment.
3. Run the scraper from the project root:
   ```bash
   python bing_image_scraper_hd.py
   ```
4. The script will create or update the [USA_Food_Collection](USA_Food_Collection) directory automatically.

### Customizing what gets collected

You can edit the `USA_DISHES` dictionary in [bing_image_scraper_hd.py](bing_image_scraper_hd.py) to change:
- which dishes are collected
- how many images are downloaded per dish
- the minimum accepted image resolution

## Data Validation

The validation workflow is implemented in [validate_auto_labels.py](validate_auto_labels.py).

### What changed
- The validator now works with the current dataset layout under [USA_Food_Collection](USA_Food_Collection).
- It can inspect either:
  - a folder-based dataset (one folder per dish), or
  - a flat dataset layout if files are stored directly in the dataset directory
- It shows images and asks the user to confirm whether the expected label is correct.

### How to run validation

From the project root, run:

```bash
python validate_auto_labels.py
```

### Validation commands

When prompted, use:
- `y` = the image matches the expected label
- `n` = the image does not match the expected label
- `s` = skip the image
- `q` = quit early and save the current results

### Output files

The validator writes CSV results during the process, including:
- `validation_2_percent_results.csv`
- `validation_5_percent_results.csv`
- `validation_8_percent_results.csv`
- `validation_10_percent_results.csv`
- `validation_final_results.csv`

## Notes

- Run the collection script before validation so the dataset exists in [USA_Food_Collection](USA_Food_Collection).
- If you change the dataset structure, the validator will still try to load it, but the folder-based layout is the recommended format.
- The scraper and validator assume you are running commands from the repository root.
- For long collection runs, keep Chrome available and avoid interrupting the process while images are being downloaded.
