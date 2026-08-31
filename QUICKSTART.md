# PNG2ANSI quickstart

Start with the output geometry, because every later decision is judged at that
resolution. The 80×40 default is a reliable Windows Terminal canvas. Increase
columns or rows only when the final viewer can show them without wrapping and
the workload estimate remains safe. Keep the 4×8 sample grid initially. The
full CP437 vocabulary gives maximum shape accuracy; `box-block` is cleaner,
while the industrial vocabularies produce a deliberately mechanical texture.

Choose `photographic` when colour blocks and recognisable shading matter.
Choose `industrial` when the image should read as sparse wiring, seams,
indicators, and structural outlines. In photographic mode, tune contrast first,
then gamma. A small contrast increase separates palette regions; gamma brightens
or darkens midtones without moving black and white as aggressively as
brightness. Adjust saturation after the tonal structure is legible. Sharpness
is already slightly raised, so avoid combining a high sharpness value with a
strong NL edge enhancement unless halos are intentional.

Derez is useful when the source contains detail that cannot survive the ANSI
grid. Enable it and begin at 160×160. Lower dimensions simplify textures and
make larger, more coherent glyph clusters; higher dimensions retain small
features. Width and height are independent, so they can also correct or create
an aspect treatment. Derez never enlarges a smaller source.

NL Filter is off by default. `edge-enhancement` with radius 1 and alpha 0.9 is
a strong starting preset for panels, diagrams, and machinery; reduce alpha if
bright rims or noisy seams appear. `alpha-trimmed-mean` removes isolated specks,
with alpha near 1 behaving like a median. `optimal-estimation` is better for
dither or grain because it smooths quiet regions while retaining stronger
features. Apply NL before compensating with contrast or sharpness.

For industrial output, raise sparsity threshold to create black space, then
restore important lines with edge weight. Texture weight adds surface grain;
accent weight preserves saturated lights and cables. Keep highlight weight low
unless broad bright plates should become filled shapes.

Leave colour candidates at 6 foreground and 5 background while composing.
Increase them only for the final photographic pass; they do not affect
industrial mode. The web app clamps background candidates to eight and blocks
unsafe workloads instead of appearing frozen. Finally inspect the PNG at its
native size, confirm the terminal width matches the configured columns, and
open the `.ans` in a CP437-compatible viewer before publishing it.
