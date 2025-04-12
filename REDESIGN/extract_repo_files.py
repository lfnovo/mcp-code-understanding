#!/usr/bin/env python3

import sys


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} repo_map_output.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = "extracted_files.txt"
    unique_files = set()

    with open(input_file) as f:
        for line in f:
            # Skip lines with special characters used for indentation/structure
            if any(c in line for c in "⋮│"):
                continue

            # Remove colons and whitespace
            line = line.strip().rstrip(":")
            if line:
                unique_files.add(line)

    # Sort the files for consistent output
    sorted_files = sorted(unique_files)

    # Print to console
    for file in sorted_files:
        print(file)
    print(f"\nTotal unique files: {len(sorted_files)}")

    # Save to file
    print(f"\nSaving file list to {output_file}")
    with open(output_file, "w") as f:
        for file in sorted_files:
            f.write(f"{file}\n")
    print(f"Saved {len(sorted_files)} files to {output_file}")


if __name__ == "__main__":
    main()
