'''
Script to upload Markdown files along with Images to Medium

References:
https://betterprogramming.pub/programmatically-publish-a-markdown-file-as-a-medium-story-with-python-b2b072a5f968
https://medium.com/@davide.gazze/publish-a-medium-post-using-python-fccbe61c04e
'''

from __future__ import annotations
from typing import Mapping, Optional, TypedDict
import os
import argparse

from colorama import Fore, Style
import requests
import markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import frontmatter  # type: ignore


class MediumPost(TypedDict, total=False):
    '''
    Type Annotation for Dictionary with Medium Post Content
    Tags is optional field
    '''

    title: str
    tags: list[str]
    publishStatus: str
    content: str
    contentFormat: str


def print_colored(
    print_content: Optional[str], foreground_color: str = Fore.LIGHTYELLOW_EX
) -> None:
    '''
    Function to create colored Output
    '''

    print(f"{foreground_color}{print_content}{Style.RESET_ALL}")


def get_headers(token: str) -> Mapping[str, str]:
    '''
    Generates header to be send with each request to Medium
    '''

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Host": "api.medium.com",
        "Authorization": f"Bearer {token}",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }

    return headers


def read_markdown_file(filepath: str) -> frontmatter.Post:
    '''
    Reads the content of markdown file
    '''

    with open(filepath, 'r', encoding='utf-8') as markdown_file:
        markdown_file_content = frontmatter.load(markdown_file)
    print_colored("Reading File Content...")

    return markdown_file_content


def read_socials_details() -> str:
    '''
    Read Author Social Links from File
    '''

    with open('config/socials.md', 'r', encoding='utf-8') as socials:
        file_content = socials.read()
    print_colored("Reading Author Social Details...")

    return file_content


def prepare_payload(filepath: str, status: str, author_details: bool) -> MediumPost:
    '''
    Generate Payload with required fields to Publish Post
    '''

    payload: MediumPost = {"contentFormat": "markdown"}

    markdown_file_content = read_markdown_file(filepath)
    post_frontmatter = markdown_file_content.metadata

    if post_frontmatter.get('title'):
        payload['title'] = post_frontmatter['title']
    else:
        payload['title'] = str(os.path.basename(filepath))

    if post_frontmatter.get('tags'):
        payload['tags'] = [
            tag.replace('-', ' ').strip().title()
            for tag in post_frontmatter['tags']
        ]

    payload['publishStatus'] = status

    post_title = f"# {payload['title']}\n\n"
    post_description = f"{post_frontmatter['description']}\n\n" if post_frontmatter.get('description') else ''
    socials_details = read_socials_details() if author_details else ''

    post_content = post_title + post_description + markdown_file_content.content + socials_details
    payload['content'] = post_content

    print_colored("Processing Post Content...")

    return payload


def get_author_id(token: str) -> str | None:
    '''
    Fetch the Author Id using the provided Token
    '''

    headers = get_headers(token)
    url = "https://api.medium.com/v1/me"

    response = requests.get(url, headers=headers, timeout=60)

    if response.status_code == 200:
        return response.json()['data']['id']
    return None


def extract_images(content: str) -> list[str]:
    """
    Find images in the source file
    """

    output = markdown.markdown(content)
    soup = BeautifulSoup(output, "html.parser")
    images_from_html = soup.find_all("img")

    extracted_images_list = []
    for image in images_from_html:
        extracted_images_list.append(image['src'])

    return extracted_images_list


def publish_image(image_path: str, headers: Mapping[str, str]) -> str | None:
    """
    Publish image to Medium CDN using API
    """

    with open(image_path, "rb") as image:
        filename = os.path.basename(image_path)
        extension = image_path.split(".")[-1]
        files = {"image": (filename, image, f"image/{extension}")}

        url = "https://api.medium.com/v1/images"
        response = requests.post(url, headers=headers, files=files, timeout=60)

        if response.status_code in [200, 201]:
            json = response.json()
            return json["data"]["url"]

    return None


def post_article(data: MediumPost, medium_token: str, filepath: str) -> str | None:
    """
    Posts an article to medium using the generated payload
    """

    headers = get_headers(medium_token)
    images_path = extract_images(data["content"])

    print_colored(f"\nFound {len(images_path)} images to upload...")
    file_absolute_path = os.path.dirname(os.path.realpath(filepath))

    for image_path in images_path:
        absolute_image_path = os.path.normpath(os.path.join(file_absolute_path, image_path))
        new_url = publish_image(absolute_image_path, headers)
        if new_url is not None:
            data["content"] = data["content"].replace(image_path, new_url)
        print_colored(f"Uploading Image: {os.path.basename(image_path)}")

    author_id = get_author_id(medium_token)
    url = f"https://api.medium.com/v1/users/{author_id}/posts"
    print_colored(f"\nPosting Article to Medium as {data['publishStatus']}...")
    response = requests.post(url, headers=headers, json=data, timeout=60)

    if response.status_code in [200, 201]:
        response_json = response.json()
        medium_post_url = response_json["data"]["url"]
        return medium_post_url

    print_colored("Error: Failed to Post Article...", Fore.LIGHTRED_EX)
    return None


def parse_user_inputs() -> argparse.Namespace:
    '''
    Function to read input parameters from user
    '''

    parser = argparse.ArgumentParser(description="Automate Publishing Articles to Medium")

    input_type = parser.add_mutually_exclusive_group(required=True)
    input_type.add_argument('-p', '--post', help="Path to Markdown File to Upload")
    input_type.add_argument(
        '-l', '--list',
        help="Path of file containing Absolute Paths of Markdown files to Upload",
    )

    parser.add_argument(
        '-a', '--author', required=False, action='store_true', default=False,
        help='Add author details/ social links to the end of each post'
    )

    parser.add_argument(
        '-s', '--status', required=False, default='draft',
        help="Status of Post when Published to Medium",
        type=str, choices=["public", "unlisted", "draft"]
    )

    user_arguments = parser.parse_args()
    return user_arguments


def upload_to_medium(filepath: str, status: str, author_details: bool) -> None:
    '''
    Function to Encapsulate Medium Post flow
    '''

    payload = prepare_payload(filepath, status, author_details)

    medium_token = os.environ['MEDIUM_AUTH_TOKEN']
    medium_post_url = post_article(payload, medium_token, filepath)
    print_colored(medium_post_url, Fore.LIGHTGREEN_EX)


def main() -> None:
    '''
    Main driver function
    '''

    load_dotenv(dotenv_path='config/token.config')

    if 'MEDIUM_AUTH_TOKEN' not in os.environ:
        print_colored('Medium Token not found...', Fore.LIGHTRED_EX)
        return

    user_arguments = parse_user_inputs()
    # print(user_arguments)

    if user_arguments.post is not None:
        upload_to_medium(user_arguments.post, user_arguments.status, user_arguments.author)
    else:
        with open(user_arguments.list, encoding='utf-8') as list_file:
            for filepath in list_file:
                upload_to_medium(filepath.rstrip('\n'), user_arguments.status, user_arguments.author)


if __name__ == "__main__":
    main()
