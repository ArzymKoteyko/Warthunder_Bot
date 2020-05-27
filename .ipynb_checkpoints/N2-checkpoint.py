l = int(input())
m = int(input())
r = int(input())

if l == 0:
    res = 0
elif m == 0:
    res = 1
elif r == 0:
    res = 2
elif m == 1:
    res = 3
elif l == 1:
    res = 4
elif r == 1:
    res = 6

elif m <= 2*l and m <= 2*r:
    res = 2*m + 1

elif l < m and l < r:
    res = 4*l
    
else:
    res = 4*r+2

print(res)