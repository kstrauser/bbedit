# Save and restore jump points

[BBEdit](https://www.barebones.com/products/bbedit/index.html) has a variety of convenient commands to jump to another place in a project. It doesn't have the equivalent of [Emacs](https://www.gnu.org/software/emacs/)'s [`xref-go-back`](https://www.gnu.org/software/emacs/manual/html_node/emacs/Looking-Up-Identifiers.html) function. That function lets you quickly jump back to the place you started from, and once I got used to it, I can't be with out it.

bbedit_jump_points is my hacky replacement for that functionality.

## Installation

Use the normal Rust `cargo` commands to build and install the `bbedit_push_point` and `bbedit_pop_point` commands in `~/.cargo/bin`

```console
$ cargo build --release
   [...]
    Finished release [optimized] target(s) in 6.99s
$ cargo install --path .
   [...]
   Replacing /Users/me/.cargo/bin/bbedit_pop_point
   Replacing /Users/me/.cargo/bin/bbedit_push_point
   [...]
```

Alternatively, use the included [justfile](https://just.systems/man/en/) like:

```console
$ just build install
```

Then add them to BBEdit's Scripts folder:

```console
$ cd ~/Library/Mobile\ Documents/iCloud~com~barebones~bbedit/Documents/Application\ Support/Scripts
$ ln -s ~/.cargo/bin/bbedit_push_point "Push current point"
$ ln -s ~/.cargo/bin/bbedit_pop_point "Pop point"
```

or

```console
$ just link
```

## Usage

Before using a command like `Go to Definition`, run the `Push current point` script to save your current location. When you're done looking at that code, run `Pop point` to get back to where you were.

## Advanced usage with Keyboard Maestro

The above works, but has a couple of drawbacks:

- You have to remember to run `Push current point` before jumping around.
- For various reasons, `Pop point` runs much more slowly if you launch it from within BBEdit.

You can use [Keyboard Maestro](https://www.keyboardmaestro.com/main/) to make this more ergonomic.

I've defined 2 macros. This takes a little extra setup, but it's worth it:

### "Push current point and Go to Definition"

The hot key `⌘.` runs:

- Select "Push current point" in the Menu "Scripts" in BBEdit
- Select "Go to Definition" in the Menu "Go" in BBEdit

Now when I'm in BBEdit and type `⌘.`, Keyboard Maestro automatically runs the `Push current point` script and then the `Go to Definition` command.

### "Pop point"

The hot key `⎇.` runs:

- "Execute Shell Script" with the value `~/.cargo/bin/bbedit_pop_point`

Ta-da! After I've used the `Push current point and Go to Definition` macro, a single shortcut returns me to the starting point. It's also _much_ faster than running the command from within BBEdit, to the point that it feels nearly instant.