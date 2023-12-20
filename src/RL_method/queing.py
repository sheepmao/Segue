import numpy as np
import scipy.stats as stats

lambda_rate = 10  # Average arrival rate of segments
mu = 300  # Average service rate
initial_buffer = 20  # Initial buffer level
max_buffer = 100  # Maximum buffer level
arrival_distribution_params = {'mean': 15, 'std_dev': 10}
service_distribution_params = {'mean': 30, 'std_dev': 3}
segment_lengths = [2,4,6,8]  # List or array of segment lengths
segment_bitrates = [3000,2000,1000,6000]  # List or array of segment bitrates
# Additional parameters...


def generate_arrival_times(distribution_params, size=1000):
    #return np.random.exponential(1/lambda_rate, size) # exponential distribution

    #return np.random.poisson(lambda_rate, size) # poisson distribution

    #return np.random.uniform(0, 1/lambda_rate, size) # uniform distribution

    #gaussian distribution
    return np.random.normal(loc=distribution_params['mean'], 
                        scale=distribution_params['std_dev'], 
                        size=size)

def generate_service_times(distribution_params, size=1000):
    #return np.random.exponential(1/mu, size) # exponential distribution

    #return np.random.poisson(mu, size) # poisson distribution

    #return np.random.uniform(0, 1/mu, size) # uniform distribution

    #gaussian distribution
    return np.random.normal(loc=distribution_params['mean'], 
                        scale=distribution_params['std_dev'], 
                        size=size)


# def calculate_buffer_levels(arrival_times, service_times, initial_buffer, max_buffer):
#     buffer_levels = [initial_buffer]
#     for arrival, service in zip(arrival_times, service_times):
#         new_level = max(buffer_levels[-1] - arrival, 0) + service
#         buffer_levels.append(min(new_level, max_buffer))
#     return buffer_levels

def calculate_buffer_levels(arrival_times, service_times, initial_buffer,max_buffer):
    buffer_levels = [initial_buffer]
    for arrival, service in zip(arrival_times, service_times):
        # New buffer level without the restriction of not going below zero
        new_level = buffer_levels[-1] - arrival + service
        buffer_levels.append(min(new_level, max_buffer))
    return buffer_levels
def calculate_stall_probability(buffer_levels):
    stalls = sum(level <= 0 for level in buffer_levels)
    return stalls / len(buffer_levels)

if __name__ == '__main__':
    arrival_times = generate_arrival_times(arrival_distribution_params, size=1000)
    service_times = generate_service_times(service_distribution_params, size=1000)
    #print("Arrival Times:", arrival_times)
    #print("Service Times:", service_times)
    buffer_levels = calculate_buffer_levels(arrival_times, service_times, initial_buffer, max_buffer)
    print("Buffer Levels:", buffer_levels)
    stall_probability = calculate_stall_probability(buffer_levels)
    print("Stall Probability:", stall_probability)
