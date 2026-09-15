# Simple if/else merging back into one block.
x = 1
y = 2
if x < y goto L_true
z = 99
goto L_end
L_true:
z = x + y
L_end:
w = z
return w
