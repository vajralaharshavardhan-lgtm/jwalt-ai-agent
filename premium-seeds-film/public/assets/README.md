# Drop-in assets

Put real Premium Seeds photos, clips, the logo and music here, named after a
slot id from `src/assets/slots.json`, e.g.

    logo.svg
    research-breeder.jpg
    field-wide.mp4
    topgun-product.png
    harvest-farmer.jpg
    music.mp3

They are picked up automatically the next time you run `npm run studio` or any
`npm run render*` command (or run `npm run assets:scan` by hand). Remove a file
to fall back to the built-in visual. See the main README for the full list.
