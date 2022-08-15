import os

# This code has been readapted from the one made available in https://github.com/hongzimao/pensieve



def load_trace(trace_filename):
    cooked_bw = []
    cooked_time = []
    assert os.path.exists(trace_filename)
    with open(trace_filename, 'rb') as f:
        for line in f:
            parse = line.split()
            cooked_time.append(float(parse[0]))
            cooked_bw.append(float(parse[1]))
    return cooked_time, cooked_bw

