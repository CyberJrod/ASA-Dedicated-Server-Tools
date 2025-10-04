import pandas as pd

def parse_ini(filename):
    """Parse INI file and return a dict of settings with '='."""
    settings = {}
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith(";"):  # skip comments
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()
    return settings

def compare_inis(old_file, new_file, output_file="GameUserSettings_ini_comparision.xlsx"):
    # Parse both files
    old_settings = parse_ini(old_file)
    new_settings = parse_ini(new_file)

    # Collect all unique keys
    all_keys = set(old_settings.keys()) | set(new_settings.keys())

    # Build comparison data
    data = []
    for key in sorted(all_keys):
        old_val = old_settings.get(key, "❌ Not in Old")
        new_val = new_settings.get(key, "❌ Not in New")
        match = "✅ Match" if old_val == new_val else "❌ Different"
        data.append([key, old_val, new_val, match])

    # Create DataFrame
    df = pd.DataFrame(data, columns=["Setting", "Old Value", "New Value", "Match?"])

    # Save to Excel
    df.to_excel(output_file, index=False)
    print(f"Comparison saved to {output_file}")

# -----------------------------
# Run it with your files
# -----------------------------
compare_inis("Old-GameUserSettings.ini", "New-GameUserSettings.ini")
