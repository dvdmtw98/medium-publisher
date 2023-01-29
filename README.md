# Medium Publisher

A python script to automate and simplify the process of publishing Markdown files as posts to Medium using the Medium REST API.
The script supports setting the Title, Subtitle and Tags of the Medium posts using Markdown Front matter.

```bash
> python .\publish.py -h

usage: publish.py [-h] (-p POST | -l LIST) [-a] [-s {public,unlisted,draft}]

Automate Publishing Articles to Medium

optional arguments:
  -h, --help            show this help message and exit
  -p POST, --post POST  Path to Markdown File to Upload
  -l LIST, --list LIST  Path of file containing Absolute Paths of Markdown files to Upload
  -a, --author          Add author details/ social links to the end of each post
  -s {public,unlisted,draft}, --status {public,unlisted,draft}
                        Status of Post when Published to Medium
```