#!/usr/bin/env python

"""Let a user converse with ChatGPT through a formatted Markdown file.

Example:
-------
```markdown
# Example conversation

What's a henweigh?

> About 3 pounds.

Is that a joke?

> Yes, it is a play on words. The term "henweigh" sounds like "how much does it weigh?" when spoken quickly. It's a humorous way to respond by giving a weight measurement in the form of a pun.
```

"""

import itertools
import json
import re
import sys
from collections.abc import Generator
from enum import StrEnum, auto
from pathlib import Path

import openai

SPACES = re.compile(r"\n(\n+)")


class Kind(StrEnum):
    """The kinds of text blocks in a Markdown ChatGPT conversation."""

    undefined = auto()
    header = auto()
    user = auto()
    assistant = auto()
    space = auto()


def load_conf() -> dict[str, str]:
    """Return the contents of the "conf.json" file in this directory as a dict."""
    return json.loads((Path(__file__).parent / "conf.json").read_bytes())


def classify(line: str) -> Kind:
    """Return the Part of a line of text."""
    if line.startswith("#"):
        return Kind.header
    if line.startswith(">"):
        return Kind.assistant
    if line.strip() == "":
        return Kind.space
    return Kind.user


def content_from(lines: list[str]) -> str:
    """Combine a list of lines into a Markdown blockquote."""
    return SPACES.sub("\n\n", "\n".join(line.lstrip(">").strip() for line in lines).strip())


def conversation_parts(lines: list[str]) -> Generator[tuple[Kind, str], None, None]:
    """Yield a sequence of (kind, content) tuples from the documents contents."""
    last_kind = Kind.undefined
    block: list[str] = []

    for kind, group in itertools.groupby(lines, key=classify):
        if last_kind == Kind.undefined:
            if kind not in {Kind.user, Kind.assistant}:
                continue
            last_kind = kind

        if kind == Kind.header:
            continue

        if kind == last_kind or kind == Kind.space:
            block.extend(group)
        else:
            yield last_kind, content_from(block)
            last_kind = kind
            block = list(group)

    if block:
        yield last_kind, content_from(block)


def format_reply(text: str) -> str:
    """Format the text as a Markdown blockquote."""
    return "\n".join(f"> {line}" for line in text.splitlines())


def process(content: str) -> str:
    """Continue a ChatGPT conversation from a Markdown file."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Please don't kill me"}
    ] + [
        {"role": kind.value, "content": content}
        for kind, content in conversation_parts(content.splitlines())
    ]

    if messages[-1]["role"] == Kind.assistant:
        return content

    conf = load_conf()
    openai.api_key = conf["api_key"]
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)

    reply = response["choices"][0]["message"]["content"]

    return content.rstrip() + "\n\n" + format_reply(reply)


def process_stdin():
    """Process a ChatGPT conversation passed in via stdin."""
    print(process(sys.stdin.read()))


if __name__ == "__main__":
    process_stdin()
