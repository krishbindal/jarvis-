"""Command specification for network and conversion operations (Phase 4)."""

NETWORK_SPEC = [
    {
        "action": "download_file",
        "type": "network",
        "phrases": [
            "download {url}",
            "download file {url}",
            "download file from {url}",
            "download",
            "download file"
        ],
    },
    {
        "action": "download_video",
        "type": "network",
        "phrases": [
            "download video {url}",
            "download from {url}",
            "download video",
            "download youtube video"
        ],
    },
    {
        "action": "convert_to_mp3",
        "type": "conversion",
        "phrases": [
            "convert {path} to mp3",
            "download {url} to mp3",
            "convert to mp3",
            "convert audio to mp3"
        ],
    },
    {
        "action": "convert_to_pdf",
        "type": "conversion",
        "phrases": [
            "convert {path} to pdf",
            "convert to pdf"
        ],
    }
]