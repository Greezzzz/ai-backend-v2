def num_generator():
    num = 0

    while True:
        print("sebelum yield")
        yield num
        print("setelah yield")
        num += 1


number = num_generator()
print("hello")
print(next(number))
print("-------------")
print(next(number))
print("-------------")
print(next(number))
print("-------------")
print(next(number))
