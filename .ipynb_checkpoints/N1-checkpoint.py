n=int(input())
m=int(input())
if n>0:
    if m>0:
        print(m+n)
    else:
        if m+n>0:
            print(m+n)
        else:
            print(m+n-1)
else:
    if m<0:
        print(m+n)
    else:
        if m+n<0:
            print(m+n)
        else:
            print(m+n+1)