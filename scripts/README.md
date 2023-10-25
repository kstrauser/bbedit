# Various stuff

## "ChatGPT conversation" text filter

This allows users to have converstations with ChatGPT using a Markdown file as an interface. For example:

```markdown
# Example conversation

What's a henweigh?

> About 3 pounds.

Is that a joke?

> Yes, it is a play on words. The term "henweigh" sounds like "how much does it weigh?" when spoken quickly. It's a humorous way to respond by giving a weight measurement in the form of a pun.
```

Users write text. The text filter adds ChatGPT's response to the end of the file as a blockquote. If the file already ends in a blockquote (i.e. it's the user's turn to write something), it returns the contents unchanged.

### Installation

Use [Poetry](https://python-poetry.org) to install the `ChatGPT conversation` script, then link that script into BBEdit's "Text Filters" directory:

```console
$ poetry install
$ ln -sf $(which "ChatGPT conversation") ~/Library/Mobile\ Documents/iCloud~com~barebones~bbedit/Documents/Application\ Support/Text\ Filters
```

Then copy the `_conf.json` file to `conf.json` and edit it to include your own OpenAI API key.

```console
$ cp _conf.json conf.json
$ bbedit conf.json
```