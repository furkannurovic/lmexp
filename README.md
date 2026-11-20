# lmexp

"Let me explain": a Claude Code mod that adds the `/lmexp` slash command. It opens a blank canvas in its own browser window where you draw or write what you mean. Press Ctrl+Enter and the picture is saved and referenced in your prompt box, ready for you to add your own words and send to Claude.

## Install

At the prompt of a Claude Code terminal session:

```
/plugin install lmexp --marketplace furkannurovic/lmexp
```

Answer `y` to add the marketplace, then pick a scope (the user scope makes it available in every session).

From a shell:

```
claude plugin install lmexp --marketplace furkannurovic/lmexp
```

In the desktop app, where `/plugin` does not run: click + next to the prompt box, then Plugins, Add marketplace with `furkannurovic/lmexp`, then Add plugin.

## Requirements

- `python3` on the PATH (standard library only).
- A Chromium-family browser (`chromium`, `google-chrome-stable`, `brave` or `microsoft-edge-stable`). Without one, the canvas opens in your default browser through `xdg-open`.

## Use

- `/lmexp` opens the canvas. Text after the command (`/lmexp this is the layout I mean`) becomes the start of your prompt.
- **Ctrl+Enter** finishes: the drawing is cropped, saved as a PNG, and a line pointing Claude at it is placed in your prompt box. Nothing is submitted until you press Enter yourself.
- **Esc** cancels (twice if you have already drawn something). Closing the window also cancels.
- Tools: pen (P), typed text (T), eraser (E), four colours, three sizes, undo (Ctrl+Z) and clear.

Drawings are kept in the plugin's data folder and removed after 7 days.

## How it works

`hooks/register.ts` registers the command and starts `canvas/canvas.py`, which serves `canvas/canvas.html` on a random localhost port behind a one-time token, opens it in a browser window, and waits for the picture.
