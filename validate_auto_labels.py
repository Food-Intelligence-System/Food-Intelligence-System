import csv
import math
import random
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image


# ============================================================
# Dataset Configuration
# ============================================================

# For the flat dataset currently present in the workspace:
DATASET_DIR = Path("USA_Food_Collection")

# If your dataset has one folder per dish, use for example:
# DATASET_DIR = Path("USA_Food_Collection")


# ============================================================
# Validation Configuration
# ============================================================

VALIDATION_STAGES = [0.02, 0.05, 0.08, 0.10]
RANDOM_SEED = 42

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
}


# ============================================================
# Image and Dataset Functions
# ============================================================

def get_image_files(folder):
    """Return supported image files directly inside a folder."""
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def group_flat_dataset(dataset_dir):
    """
    Group images from a flat directory by their filename label.

    Examples:
        Apple_Pie_1.jpg -> Apple Pie
        Chicken_Nuggets_25.jpg -> Chicken Nuggets
        BBQ_Chicken_8.jpg -> BBQ Chicken
    """
    grouped_images = defaultdict(list)

    for image_path in get_image_files(dataset_dir):
        filename_without_extension = image_path.stem

        label, separator, image_number = (
            filename_without_extension.rpartition("_")
        )

        if not separator or not image_number.isdigit():
            print(
                f"Skipping file with unknown label format: "
                f"{image_path.name}"
            )
            continue

        readable_label = label.replace("_", " ")
        grouped_images[readable_label].append(image_path)

    return dict(grouped_images)


def load_dataset(dataset_dir):
    """
    Load either a folder-based or flat dataset.

    Supported folder-based structure:

        dataset/
        ├── Apple Pie/
        │   ├── image_1.jpg
        │   └── image_2.jpg
        └── Cheesecake/
            ├── image_1.jpg
            └── image_2.jpg

    Supported flat structure:

        dataset/
        ├── Apple_Pie_1.jpg
        ├── Apple_Pie_2.jpg
        └── Cheesecake_1.jpg
    """
    dish_folders = sorted(
        folder
        for folder in dataset_dir.iterdir()
        if folder.is_dir()
    )

    folder_dataset = {}

    for dish_folder in dish_folders:
        image_files = get_image_files(dish_folder)

        if image_files:
            folder_dataset[dish_folder.name] = image_files

    if folder_dataset:
        print("Dataset format detected: one folder per dish")
        return folder_dataset

    flat_dataset = group_flat_dataset(dataset_dir)

    if flat_dataset:
        print("Dataset format detected: flat files grouped by filename")
        return flat_dataset

    return {}


def select_additional_samples(
    image_files,
    validated_images,
    target_sample_size,
):
    """
    Select only the additional images needed to reach the target sample size.

    Previously reviewed images are never selected again.
    """
    previously_reviewed_count = sum(
        image_path in validated_images
        for image_path in image_files
    )

    additional_sample_size = max(
        0,
        target_sample_size - previously_reviewed_count,
    )

    remaining_images = [
        image_path
        for image_path in image_files
        if image_path not in validated_images
    ]

    additional_sample_size = min(
        additional_sample_size,
        len(remaining_images),
    )

    return random.sample(
        remaining_images,
        additional_sample_size,
    )


# ============================================================
# Human Validation Functions
# ============================================================

def ask_for_validation():
    """Ask the user to validate the displayed image."""
    while True:
        answer = input(
            "\nIs this image correctly labeled? "
            "[y = correct, n = incorrect, s = skip, q = quit]: "
        ).strip().lower()

        if answer in {"y", "n", "s", "q"}:
            return answer

        print("Invalid input. Please enter y, n, s, or q.")


def show_image(image_path, dish_name, image_number, total_images):
    """Display an image with its expected label."""
    try:
        with Image.open(image_path) as image:
            plt.figure(figsize=(10, 8))
            plt.imshow(image)
            plt.axis("off")
            plt.title(
                f"Expected label: {dish_name}\n"
                f"Image {image_number} of {total_images}\n"
                f"{image_path.name}"
            )
            plt.tight_layout()
            plt.show()
            plt.close()

    except Exception as error:
        print(f"Could not display {image_path}: {error}")


# ============================================================
# Results and Accuracy Functions
# ============================================================

def calculate_accuracy(results):
    """
    Calculate accuracy using only correct and incorrect responses.

    Skipped images are excluded from the accuracy calculation.
    """
    completed_results = [
        result
        for result in results
        if result["validation_result"] in {"correct", "incorrect"}
    ]

    if not completed_results:
        return 0, 0, 0.0

    correct_count = sum(
        result["validation_result"] == "correct"
        for result in completed_results
    )

    verified_count = len(completed_results)
    accuracy = (correct_count / verified_count) * 100

    return correct_count, verified_count, accuracy


def save_results(results, results_file):
    """Save validation results to a CSV file."""
    fieldnames = [
        "validation_stage",
        "dish_label",
        "image_path",
        "validation_result",
    ]

    with open(results_file, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def print_summary(results, selected_counts, stage_percentage):
    """Print per-dish and overall accuracy for the current stage."""
    print("\n" + "=" * 70)
    print(
        f"VALIDATION SUMMARY - "
        f"{stage_percentage * 100:.0f}% STAGE"
    )
    print("=" * 70)

    results_by_dish = defaultdict(list)

    for result in results:
        results_by_dish[result["dish_label"]].append(result)

    for dish_name in sorted(selected_counts):
        dish_results = results_by_dish[dish_name]

        correct_count, verified_count, accuracy = (
            calculate_accuracy(dish_results)
        )

        incorrect_count = sum(
            result["validation_result"] == "incorrect"
            for result in dish_results
        )

        skipped_count = sum(
            result["validation_result"] == "skipped"
            for result in dish_results
        )

        print(f"\nDish: {dish_name}")
        print(
            f"  Images in dataset: "
            f"{selected_counts[dish_name]['total_images']}"
        )
        print(
            f"  Target sample size: "
            f"{selected_counts[dish_name]['target_sample_size']}"
        )
        print(f"  Verified: {verified_count}")
        print(f"  Correct: {correct_count}")
        print(f"  Incorrect: {incorrect_count}")
        print(f"  Skipped: {skipped_count}")

        if verified_count > 0:
            print(f"  Accuracy: {accuracy:.2f}%")
        else:
            print("  Accuracy: Not available")

    correct_count, verified_count, accuracy = (
        calculate_accuracy(results)
    )

    incorrect_count = sum(
        result["validation_result"] == "incorrect"
        for result in results
    )

    skipped_count = sum(
        result["validation_result"] == "skipped"
        for result in results
    )

    print("\n" + "-" * 70)
    print("OVERALL RESULTS")
    print("-" * 70)
    print(f"Total verified images: {verified_count}")
    print(f"Correct labels: {correct_count}")
    print(f"Incorrect labels: {incorrect_count}")
    print(f"Skipped images: {skipped_count}")

    if verified_count > 0:
        print(f"Overall auto-labeling accuracy: {accuracy:.2f}%")
    else:
        print("Overall accuracy: Not available")


# ============================================================
# Main Validation Workflow
# ============================================================

def main():
    if not DATASET_DIR.exists():
        print(f"Dataset directory does not exist: {DATASET_DIR}")
        return

    if not DATASET_DIR.is_dir():
        print(f"Dataset path is not a directory: {DATASET_DIR}")
        return

    random.seed(RANDOM_SEED)

    dish_images = load_dataset(DATASET_DIR)

    if not dish_images:
        print(f"No labeled images found inside: {DATASET_DIR}")
        return

    all_results = []

    # Images in this set will not be displayed again in later stages.
    validated_images = set()

    print("\n" + "=" * 70)
    print("AUTO-LABEL VALIDATION")
    print("=" * 70)
    print(f"Dataset directory: {DATASET_DIR}")
    print(f"Dish labels found: {len(dish_images)}")
    print("Validation stages: 2%, 5%, 8%, and 10%")

    print("\nInstructions:")
    print("  y = image matches its expected label")
    print("  n = image does not match its expected label")
    print("  s = skip image")
    print("  q = stop and save the current results")

    validation_stopped = False

    for stage_percentage in VALIDATION_STAGES:
        stage_samples = []
        selected_counts = {}

        for dish_name, image_files in sorted(dish_images.items()):
            total_images = len(image_files)

            target_sample_size = max(
                1,
                math.ceil(total_images * stage_percentage),
            )

            target_sample_size = min(
                target_sample_size,
                total_images,
            )

            new_samples = select_additional_samples(
                image_files=image_files,
                validated_images=validated_images,
                target_sample_size=target_sample_size,
            )

            selected_counts[dish_name] = {
                "total_images": total_images,
                "target_sample_size": target_sample_size,
            }

            for image_path in new_samples:
                stage_samples.append((dish_name, image_path))

        random.shuffle(stage_samples)

        print("\n" + "=" * 70)
        print(
            f"STARTING {stage_percentage * 100:.0f}% VALIDATION STAGE"
        )
        print("=" * 70)
        print(f"New images to review: {len(stage_samples)}")
        print(f"Images already reviewed: {len(validated_images)}")

        for index, (dish_name, image_path) in enumerate(
            stage_samples,
            start=1,
        ):
            print("\n" + "-" * 70)
            print(
                f"{stage_percentage * 100:.0f}% stage - "
                f"image {index} of {len(stage_samples)}"
            )
            print(f"Expected label: {dish_name}")
            print(f"Image: {image_path}")

            show_image(
                image_path=image_path,
                dish_name=dish_name,
                image_number=index,
                total_images=len(stage_samples),
            )

            answer = ask_for_validation()

            if answer == "q":
                print("\nValidation stopped by the user.")
                validation_stopped = True
                break

            if answer == "y":
                validation_result = "correct"
            elif answer == "n":
                validation_result = "incorrect"
            else:
                validation_result = "skipped"

            all_results.append(
                {
                    "validation_stage": (
                        f"{stage_percentage * 100:.0f}%"
                    ),
                    "dish_label": dish_name,
                    "image_path": str(image_path),
                    "validation_result": validation_result,
                }
            )

            # Skipped images are treated as reviewed and are not shown
            # again in a later stage. They remain excluded from accuracy.
            validated_images.add(image_path)

        results_file = (
            f"validation_{stage_percentage * 100:.0f}_percent_results.csv"
        )

        save_results(all_results, results_file)
        print_summary(
            results=all_results,
            selected_counts=selected_counts,
            stage_percentage=stage_percentage,
        )

        print(f"\nResults saved to: {results_file}")

        if validation_stopped:
            break

    print("\n" + "=" * 70)
    print("VALIDATION PROCESS FINISHED")
    print("=" * 70)
    print(f"Total images reviewed: {len(validated_images)}")

    if all_results:
        final_results_file = "validation_final_results.csv"
        save_results(all_results, final_results_file)
        print(f"Complete results saved to: {final_results_file}")


if __name__ == "__main__":
    main()