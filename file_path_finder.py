import os

def print_directory_tree(start_path='.', max_depth=None, output_file=None):
    """
    Prints the directory structure in a tree-like format.
    
    Args:
    - start_path (str): Root directory path.
    - max_depth (int or None): Maximum depth to print. None = unlimited.
    - output_file (str or None): Path to a file to save the output instead of printing.
    """

    def walk(current_path, prefix='', depth=0):
        if max_depth is not None and depth > max_depth:
            return
        entries = sorted(os.listdir(current_path))
        for idx, entry in enumerate(entries):
            path = os.path.join(current_path, entry)
            connector = '└── ' if idx == len(entries) - 1 else '├── '
            line = f"{prefix}{connector}{entry}"
            lines.append(line)
            if os.path.isdir(path):
                extension = '    ' if idx == len(entries) - 1 else '│   '
                walk(path, prefix + extension, depth + 1)

    lines = []
    walk(start_path)
    tree_output = '\n'.join(lines)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(tree_output)
    else:
        print(tree_output)

if __name__ == "__main__":
    # Example usage:
    # Set start_path = "." to start from the current directory
    # Set max_depth = 3 to limit depth to 3 levels (or None for unlimited)
    # Set output_file = "structure.txt" to save it to a text file

    print_directory_tree(start_path='.', max_depth=None, output_file='structure.txt')

