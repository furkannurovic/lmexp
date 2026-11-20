import type { Register } from 'claude-code'

// One canvas at a time per session. A reload resets this, and also ends the
// helper process, so the two stay in step.
let isCanvasOpen = false

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'lmexp',
      description:
        'Let me explain: draw or write on a blank canvas, Ctrl+Enter puts the picture in your prompt',
      argumentHint: '[a note to start the prompt with]',
    })

    return next(e)
  })

  on('command.run', { command: 'lmexp' }, async ($, e) => {
    if (isCanvasOpen) {
      return {
        text: 'A canvas is already open. Press Ctrl+Enter in it to send, or Esc to cancel.',
        isTextDisplayOnly: true,
      }
    }
    isCanvasOpen = true
    const note = e.args.trim()

    // The canvas lives as long as the person draws, so the wait runs on after
    // this hook has answered.
    void (async () => {
      try {
        const env = await $.process.hookEnv()
        const outDir = env.CLAUDE_PLUGIN_DATA ?? '/tmp/lmexp'
        const helper = $.process.spawn({
          argv: ['python3', `${$.plugin.root}/canvas/canvas.py`, outDir],
        })
        let stdout = ''
        let stderr = ''
        for await (const { stream, text } of helper) {
          if (stream === 'stdout') stdout += text
          else stderr += text
        }

        const last = stdout.trim().split('\n').pop() ?? ''
        if (last.startsWith('SAVED ')) {
          const path = last.slice('SAVED '.length)
          // Into the prompt box, not submitted: the person adds their own
          // words after it and presses Enter themselves.
          const draft =
            `Let me explain with a drawing. I drew it on a canvas and it is saved at ${path}. ` +
            'Look at it with the Read tool, then respond to what it shows.\n\n' +
            (note ? `${note} ` : '')
          const { text: typed } = await $.prompt.read()
          const { isFilled } = await $.prompt.fill({
            text: typed.trim() ? `\n\n${draft}` : draft,
            mode: 'append',
          })
          if (!isFilled) $.ui.toast(`lmexp: drawing saved at ${path}, but the prompt box was busy`)
        } else if (last === 'CANCELLED') {
          $.ui.toast('lmexp: canvas closed, nothing sent')
        } else {
          const reason = (last.startsWith('ERROR ') ? last.slice(6) : stderr.trim().split('\n').pop()) || 'the canvas helper stopped'
          $.ui.toast(`lmexp: ${reason}`)
        }
      } catch (error) {
        $.ui.toast(`lmexp: ${error instanceof Error ? error.message : String(error)}`)
      } finally {
        isCanvasOpen = false
      }
    })()

    return {
      text: 'Canvas opened. Draw or write, then press Ctrl+Enter to put it in your prompt (Esc cancels).',
      isTextDisplayOnly: true,
    }
  })
}
