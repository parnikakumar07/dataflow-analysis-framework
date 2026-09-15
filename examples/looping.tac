# A while-style loop -- exercises back-edges and fixpoint iteration.
i = 0
s = 0
L_head:
if i < 10 goto L_body
goto L_end
L_body:
s = s + i
i = i + 1
goto L_head
L_end:
return s
