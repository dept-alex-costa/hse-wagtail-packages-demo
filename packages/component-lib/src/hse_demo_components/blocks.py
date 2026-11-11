"""A small block shared in shape, independently released in each line."""

from wagtail import blocks


class DemoCardBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    body = blocks.TextBlock(required=False)

    class Meta:
        icon = "doc-full"
        label = "Demo card"
