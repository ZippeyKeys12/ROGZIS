set NAME=rogzis
if not exist "dist" mkdir "dist"
cd src
..\tools\7za a -tzip %NAME%.pk3 *.* *
move %NAME%.pk3 ../dist/%NAME%.pk3