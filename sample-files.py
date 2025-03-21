import os
import random
import shutil


def sample_files(source_folder, destination_folder, sample_size):
    """
    Create a random sample of files from a source folder and copy them to a destination folder.

    Args:
        source_folder (str): Path to the folder containing all files
        destination_folder (str): Path to the folder where sampled files will be copied
        sample_size (int): Number of files to sample
    """
    # Get all files from source directory
    all_files = [
        f
        for f in os.listdir(source_folder)
        if os.path.isfile(os.path.join(source_folder, f))
    ]

    # Check if sample size is valid
    if sample_size > len(all_files):
        sample_size = len(all_files)
        print(
            f"Sample size adjusted to {sample_size} (total number of files available)"
        )

    # Select random files
    sampled_files = random.sample(all_files, sample_size)

    # Create destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)

    # Copy sampled files to destination
    for file in sampled_files:
        source_path = os.path.join(source_folder, file)
        dest_path = os.path.join(destination_folder, file)
        shutil.copy2(source_path, dest_path)

    print(f"Successfully copied {len(sampled_files)} files to {destination_folder}")


# Example usage
if __name__ == "__main__":
    sample_files(
        "/mnt/cfdd0ae1-0c7a-4e06-b98a-c7d8977986aa/Dropbox/Camera Uploads",
        "sample_directory",
        10,
    )
