max_len = int(input())
n = int(input())

A = []


for i in range(n):
    A.append(int(input()))
count = 0

res = [0 for i in range(len(A))]
res.append(0)
res.append(0)
res.append(0)

for i in range(len(A)-1):
    if A[i] == 1 and res[i] == 0:
        for j in range(max_len):
            if j < len(A)-1:
                res[i+j] = max_len
                count += 1
print(count//max_len) 