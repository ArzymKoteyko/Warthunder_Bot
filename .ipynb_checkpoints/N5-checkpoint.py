a = int(input())
b = int(input())
sum = 0
k=0
for i in range(a,b+1):
    while i>0:
        sum += i % 10
        i = i // 10
    if sum % 2 != 0:
        k+=1
    sum = 0
print(k)