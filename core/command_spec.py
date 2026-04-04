"""Command specification for file operations (Phase 3)."""

COMMAND_SPEC = [
    {
        "action": "list_files",
        "phrases": [
            "list files in {path}",
            "show files in {path}",
            "list directory {path}",
        ],
    },
    {
        "action": "create_folder",
        "phrases": [
            "create folder {name}",
            "make folder {name}",
            "create directory {name}",
            "new folder {name} in {path}",
        ],
    },
    {
        "action": "delete_file",
        "phrases": [
            "delete file {path}",
            "remove file {path}",
        ],
    },
    {
        "action": "move_file",
        "phrases": [
            "move file {src} to {dest}",
            "move {src} to {dest}",
        ],
    },
    {
        "action": "copy_file",
        "phrases": [
            "copy file {src} to {dest}",
            "copy {src} to {dest}",
        ],
    },
    {
        "action": "rename_file",
        "phrases": [
            "rename file {path} to {new_name}",
            "rename {path} to {new_name}",
        ],
    },
    {
        "action": "search_file",
        "phrases": [
            "search file {name} in {root_path}",
            "find file {name} in {root_path}",
            "search for file {name} in {root_path}",
        ],
    },
    {
        "action": "file_info",
        "phrases": [
            "file info {path}",
            "info for file {path}",
            "details for file {path}",
        ],
    },
]
