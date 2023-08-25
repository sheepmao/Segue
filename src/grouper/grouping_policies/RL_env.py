import gym
from gym import spaces
from src.simulator.environment import Environment
class VideoStreamingEnv(gym.Env):
    """
    Custom Video Streaming Environment that follows gym interface.
    This environment is built upon the SEGUE simulator.
    """
    metadata = {'render.modes': ['human']}
    
    def __init__(self, trace):
        super(VideoStreamingEnv, self).__init__()
        
        # Initialize the SEGUE simulator environment
        self.env = Environment(trace)
        
        # Action space: 
        # 1. Segment boundary (from 0 to 480)
        # 2. CRF value (continuous value, we can limit it within a range, e.g., [0, 51])
        self.action_space = spaces.Tuple((spaces.Discrete(481), spaces.Box(low=0, high=51, shape=(1,))))
        
        # State space:
        # 1. Bandwidth (from trace)
        # 2. Buffer size (continuous)
        # 3. Previous action (segment boundary and CRF value)
        # 4. Video features (using a large number for now, can be refined)
        self.observation_space = spaces.Tuple((
            spaces.Box(low=0, high=np.inf, shape=(1,)),
            spaces.Box(low=0, high=np.inf, shape=(1,)),
            spaces.Tuple((spaces.Discrete(481), spaces.Box(low=0, high=51, shape=(1,)))),
            spaces.Box(low=0, high=1, shape=(1024,))  # Placeholder for video features
        ))
        
        self.current_state = None
        # Note: We have defined the state space, but further integration is needed to extract these values from the simulator.
        # Also, video features are not defined here as more information is needed.


    def step(self, action):
        """
        Run one timestep of the environment's dynamics.
        """
        # Extract action values
        segment_boundary, crf_value = action

        # TODO: Apply the action in the simulator environment
        # (this might involve encoding the video segment using the specified CRF value)

        #perform real encoding to get segment info
        encoded_segment = real_encoding(segment_boundary, crf_value)

        #get segment info from encoded segment
        segment_size, segment_duration = get_segment_info(encoded_segment)
        #Fetch chunk info from the SEGUE simulator environment

        chunk_info = self.env.fetch_chunk(segment_size, segment_duration)

        # TODO: Update self.current_state based on the simulator's feedback
        self.current_state = update_state(chunk_info, video_features)

        # Calculate reward
        reward = self.calculate_reward()

        # Check if the episode (video) is done
        done = False  # Placeholder, should be updated based on the simulator's state
        
        return self.current_state, reward, done, {}
    def real_encoding(self, segment_boundary, crf_value):
        # Perform real encoding using the given parameters
        # ...

        return encoded_segment    
    
    def get_segment_info(self, encoded_segment):
        # Get the segment size and duration using tools like ffprobe
        # ...

        return segment_size, segment_duration
    def update_state(self, chunk_info):
        # Update the state based on simulator feedback
        # Include bandwidth, buffer size, previous action, and video features
        # ...

        return new_state
    def reset(self):
        """
        Reset the environment to its initial state.
        """
        # TODO: Reset the simulator environment
        
        self.current_state = None  # TODO: Set the initial state based on the simulator's state
        return self.current_state
    def is_done(self):
        # Define termination criteria for the environment
        # ...

        return done

    def render(self, mode='human'):
        """
        Render the environment.
        """
        pass

    def close(self):
        """
        Close the environment.
        """
        pass

    def calculate_reward(self):
        """
        Calculate the reward based on the current state and the previous action.
        """
        # TODO: Calculate reward based on the simulator's feedback, considering factors like VMAF, segment size, duration, etc.
        reward = 0  # Placeholder
        return reward
    def calculate_reward(chunk_info, segment_size, segment_duration, vmaf_score):
        # VMAF Reward: Higher VMAF score indicates better video quality
        vmaf_reward = vmaf_score

        # Size Reward: Encourage efficient encoding (smaller size for given quality)
        size_reward = -segment_size

        # Duration Reward: Encourage shorter segment duration   #####considertaion
        duration_reward = -segment_duration

        # Rebuffering Penalty: Penalize rebuffering events
        rebuffer_penalty = -chunk_info['rebuf']

        # Combine the components with appropriate weights
        total_reward = (vmaf_reward_weight * vmaf_reward +
                        size_reward_weight * size_reward +
                        duration_reward_weight * duration_reward +
                        rebuffer_penalty_weight * rebuffer_penalty)

        return
