def write_to_file(filename, data):
    with open(filename, "w") as file:
        file.write(data)
        print(f"Data written to {filename}")

def read_from_file(filename):
    with open(filename, "r") as file:
        data = file.read().strip()
        print(f"Data read from {filename}: {data}")
        return data