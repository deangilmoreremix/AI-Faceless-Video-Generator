from openai import OpenAI
import os

def get_script(topic, api_key):
    client = OpenAI(api_key=api_key)

    system = '''
    You are a script generator. Given a topic by a user, write a script for an interesting YouTube short.
    The script should be fast-paced, attention-grabbing, and include hooks to keep the viewer engaged.
    Please only return the script content, with no additional commentary or formatting.
    '''

    print("Getting Script from Topic ")
    response = client.chat.completions.create(
        model="gpt-4o-2024-05-13",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": topic + system}
        ]
    )

    json_string = response.choices[0].message.content
    print(json_string)
    return json_string
