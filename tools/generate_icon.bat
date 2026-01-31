@echo off
REM Requires ImageMagick installed and available as `magick`.
magick convert laujuc/resources/laujuc_icon.svg -background none -define icon:auto-resize=256,128,64,48,32,16 laujuc/resources/laujuc_icon.ico
echo Icon written to laujuc/resources/laujuc_icon.ico
