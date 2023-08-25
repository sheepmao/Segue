## Video configurations instructions

Please use the TEMPLATE.json as a template for
referencing your video.
List of parameters:

- **video\_path**: path to the source video file (in our work we used h264 encoded 4k videos).
- **name**: video id.
- **resolutions**: list of resolutions in decreaseing order at which the video should be encoded, separated by space (e.g. 1920x1080 1280x720 ...).
- **video\_extension**: video container extension (in our work we used mp4).
- **video\_codec**: codec to be used during the encoding process (the only one supported in the released Segue version is h264).
