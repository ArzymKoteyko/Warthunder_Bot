lene = int(input())

A = []

for i in range(lene):
    A.append(int(input()))
B = [0 for i in range(len(A)-1)]
    
m = 0
l = 0
for i in range(len(A)-1):
    if A[i] > A[i+1]:
        m += 1
    if A[i] < A[i+1]:
        l += 1
        
if l != len(A) - 1 and m != len(A) - 1: 
    for i in range(len(A)-4):
        if A[i] < A[i+1]:
            d = i
            #[d] += 1
            c = d
            while A[c+1] >= A[c]:
                B[d] += 1
                c += 1

    mini = 10000000000
    for i in range(len(B)):
        if B[i] < mini and B[i] != 0:
            idi = i
            mini = B[i]
            
    print(idi+1)
    print(idi + mini + 2)

else:
    print(0)