"""Command specification for network and conversion operations (Phase 4)."""

NETWORK_SPEC = [
    {
        "action": "download_file",
        "type": "network",
        "phrases": [
            "download {url}",
            "download file {url}",
        ],
    },
    {
        "action": "download_video",
        "type": "network",
        "phrases": [
            "download video {url}",
            "download from {url}",
        ],
    },
    {
        "action": "convert_to_mp3",
        "type": "conversion",
        "phrases": [
            "convert {path} to mp3",
            "download {url} to mp3",
        ],
    },
    {
        "action": "convert_to_pdf",
        "type": "conversion",
        "phrases": [
            "convert {path} to pdf",
        ],
    },
]
