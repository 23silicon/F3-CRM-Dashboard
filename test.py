a = {1:(2,3,4,5), 5:(6,5,1,2), 3:(3,1,4,6)}
print([key for key,_ in a.items()])
b = sorted(a.items(), key=lambda x: x[1][3])
print(dict(b))