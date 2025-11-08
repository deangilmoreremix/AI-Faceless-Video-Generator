import os

def generate_video(image_path, audio_path, result_dir):
    # This is a simplified command. We'll need to adjust the paths to work with the web app structure.
    # Also, SadTalker needs to be installed and configured in the environment.
    command = f"python3.8 inference.py --driven_audio {audio_path} --source_image {image_path} --result_dir {result_dir} --still --preprocess full --enhancer gfpgan"
    os.system(command)

    # Return the path to the generated video
    results = sorted(os.listdir(result_dir))
    mp4_name = [f for f in results if f.endswith('.mp4')][0]
    return os.path.join(result_dir, mp4_name)
