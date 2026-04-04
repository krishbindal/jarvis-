"""Command specification for file operations (Phase 3)."""

COMMAND_SPEC = [
    {
        "action": "list_files",
        "phrases": [
            "list files in {path}",
            "show files in {path}",
            "list directory {path}",
            "list files in",
            "show files in",
            "list files"
        ],
        "default_path": "~/Downloads"
    },
    {
        "action": "create_folder",
        "phrases": [
            "create folder {name}",
            "make folder {name}",
            "create directory {name}",
            "new folder {name} in {path}",
            "create folder"
        ]
    },
    {
        "action": "delete_file",
        "phrases": [
            "delete file {path}",
            "remove file {path}",
            "delete file",
            "remove file"
        ]
    },
    {
        "action": "move_file",
        "phrases": [
            "move file {src} to {dest}",
            "move {src} to {dest}",
            "move file"
        ]
    },
    {
        "action": "copy_file",
        "phrases": [
            "copy file {src} to {dest}",
            "copy {src} to {dest}",
            "copy file"
        ]
    },
    {
        "action": "rename_file",
        "phrases": [
            "rename file {path} to {new_name}",
            "rename {path} to {new_name}",
            "rename file"
        ]
    },
    {
        "action": "search_file",
        "phrases": [
            "search file {name} in {root_path}",
            "find file {name} in {root_path}",
            "search for file {name} in {root_path}",
            "search file",
            "find file"
        ]
    },
    {
        "action": "file_info",
        "phrases": [
            "file info {path}",
            "info for file {path}",
            "details for file {path}",
            "file info"
        ]
    }
]