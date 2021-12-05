import numpy as np
import matplotlib.pyplot as plt


def line_index_val(line):
    split_line = line.split(" x")
    index = int(split_line[-1]) - 1
    val = float(split_line[0])
    return index, val


def parse_bounds(line):
    split_line = line.split("x")
    index = int(split_line[-1].split("<")[0]) - 1
    lb = float(split_line[0].split("<")[0])
    ub = float(split_line[-1].split("=")[-1])
    return index, lb, ub


def parse_lp(file):
    with open(file) as f:
        lines = f.readlines()

    i = 0
    while "min" not in lines[i]:
        i += 1

    n = int(lines[i + 1].split("x")[-1].split(":")[0]) - 1

    c = np.zeros((1, n))

    i += 2

    while "x" in lines[i]:
        index, val = line_index_val(lines[i])
        c[:, index] = val
        i += 1

    while ":" not in lines[i]:
        i += 1
    i += 1
    A = np.zeros((1, n))
    b = np.zeros((1, 1))
    while "bounds" not in lines[i]:
        try:
            a_row = np.zeros((1, n))
            b_row = np.zeros((1, 1))
            while "x" in lines[i]:
                index, val = line_index_val(lines[i])
                a_row[:, index] = val
                i += 1
            b_row[0, 0] = float(lines[i].split("=")[-1])
            if "<=" in lines[i]:
                A = np.append(A, a_row, axis=0)
                b = np.append(b, b_row, axis=0)
            elif ">=" in lines[i]:
                A = np.append(A, -a_row, axis=0)
                b = np.append(b, -b_row, axis=0)
            else:
                A = np.append(A, a_row, axis=0)
                b = np.append(b, b_row, axis=0)
                A = np.append(A, -a_row, axis=0)
                b = np.append(b, -b_row, axis=0)
            i += 3
        except ValueError:

            break

    A = A[1:, :]
    b = b[1:, :]

    while "x" in lines[i]:
        a_row = np.zeros((1, n))
        b_row_lb = np.zeros((1, 1))
        b_row_ub = np.zeros((1, 1))
        index, lb, ub = parse_bounds(lines[i])
        a_row[:, index] = 1
        b_row_lb[0, 0] = lb
        b_row_ub[0, 0] = ub
        A = np.append(A, a_row, axis=0)
        b = np.append(b, b_row_ub, axis=0)
        A = np.append(A, -a_row, axis=0)
        b = np.append(b, -b_row_lb, axis=0)
        i += 1

    return A, b, c


A, b, c = parse_lp("biomass_supply_chain.lp")

plt.figure()
plt.imshow(A, cmap="gray_r", vmin=0, vmax=0.0001)
plt.show()
