import traci
import time
import sys

# SCENARIO = "EMERGENCY_GRID".
# "DUMB_CITY" : Fixed-timer traffic lights.
# "SMART_CITY": AI optimizes traffic flow based on pressure.
# "EMERGENCY_GRID": AI optimizes traffic AND creates a green corridor for emergency vehicles.
SCENARIO = "SMART_CITY" # <--- CHANGE THIS VALUE TO SWITCH SCENARIOS

# --- Configuration ---
SUMO_CMD_GUI = ["sumo-gui", "-c", "intersection.sumocfg", "--step-length", "0.5"]

class TrafficController:
    def __init__(self):
        traci.start(SUMO_CMD_GUI)
        self.step = 0
        self.traffic_light_id = "J1"

        # Define the phases for the judges: A simple N-S green and E-W green
        self.PHASE_NS_GREEN = 0  # Phase for North-South traffic
        self.PHASE_EW_GREEN = 2  # Phase for East-West traffic
        
        # All incoming lanes, for calculating pressure
        self.incoming_lanes = [
            "N_to_J1_0", "N_to_J1_1", "N_to_J1_2",
            "S_to_J1_0", "S_to_J1_1", "S_to_J1_2",
            "E_to_J1_0", "E_to_J1_1", "E_to_J1_2",
            "W_to_J1_0", "W_to_J1_1", "W_to_J1_2"
        ]
        
    def run_step(self):
        """Runs a single simulation step and calls the appropriate logic."""
        traci.simulationStep()
        self.step += 1

        if SCENARIO == "DUMB_CITY":
            self.dumb_city_logic()
        elif SCENARIO == "SMART_CITY":
            self.smart_city_logic()
        elif SCENARIO == "EMERGENCY_GRID":
            # Emergency logic first, as it's the highest priority
            if not self.emergency_grid_logic():
                # If no emergency is active, fall back to smart traffic management
                self.smart_city_logic()
        
    def dumb_city_logic(self):
        """Fixed-timer logic. Switches every 30 seconds regardless of traffic."""
        if self.step % 60 == 0: # 60 steps = 30 seconds
            current_phase = traci.trafficlight.getPhase(self.traffic_light_id)
            if current_phase == self.PHASE_NS_GREEN:
                traci.trafficlight.setPhase(self.traffic_light_id, self.PHASE_EW_GREEN)
            else:
                traci.trafficlight.setPhase(self.traffic_light_id, self.PHASE_NS_GREEN)

    def smart_city_logic(self):
        """
        Dynamic AI logic based on 'pressure'.
        Pressure = sum of wait times of all cars on incoming lanes.
        """
        ns_pressure = self.calculate_pressure(["N_to_J1", "S_to_J1"])
        ew_pressure = self.calculate_pressure(["E_to_J1", "W_to_J1"])

        current_phase = traci.trafficlight.getPhase(self.traffic_light_id)

        # If N-S is green, but E-W pressure is much higher, consider switching
        if current_phase == self.PHASE_NS_GREEN and ew_pressure > ns_pressure * 1.5:
             traci.trafficlight.setPhase(self.traffic_light_id, self.PHASE_EW_GREEN)
             print(f"Step {self.step}: High E-W pressure ({ew_pressure:.0f} vs {ns_pressure:.0f}). Switching to E-W green.")

        # If E-W is green, but N-S pressure is much higher, consider switching
        elif current_phase == self.PHASE_EW_GREEN and ns_pressure > ew_pressure * 1.5:
             traci.trafficlight.setPhase(self.traffic_light_id, self.PHASE_NS_GREEN)
             print(f"Step {self.step}: High N-S pressure ({ns_pressure:.0f} vs {ew_pressure:.0f}). Switching to N-S green.")

    def calculate_pressure(self, from_edges):
        """Calculates the total waiting time for a set of approach edges."""
        pressure = 0
        for edge in from_edges:
            for i in range(3): # For each of the 3 lanes
                lane_id = f"{edge}_{i}"
                pressure += traci.lane.getWaitingTime(lane_id)
        return pressure

    def emergency_grid_logic(self):
        """Detects an emergency vehicle and creates a green corridor."""
        try:
            # Check if our ambulance is in the simulation
            ambulance_route = traci.vehicle.getRoute("ambulance")
            # Get the edge the ambulance is currently on, and the next one in its route
            current_edge = traci.vehicle.getRoadID("ambulance")
            
            # Find which edge is next in the ambulance's path
            next_edge_index = (ambulance_route.index(current_edge) + 1) % len(ambulance_route)
            next_edge = ambulance_route[next_edge_index]

            # THE GREEN CORRIDOR LOGIC
            # If the ambulance is approaching our intersection...
            if "to_J1" in current_edge or "to_J1" in next_edge:
                # ...force the lights green for its path!
                print(f"Step {self.step}: EMERGENCY! Ambulance approaching. Creating green corridor.")
                # This is a simplified example; a real system would calculate the exact path.
                # For this demo, we'll just set the N-S path green.
                traci.trafficlight.setPhase(self.traffic_light_id, self.PHASE_NS_GREEN)
                return True # Indicate that emergency logic was triggered
        except traci.TraCIException:
            # This happens if the ambulance is not yet in or has left the simulation.
            return False
        return False

    def run(self):
        """Main loop for the simulation."""
        print(f"Starting simulation with SCENARIO: {SCENARIO}")
        while self.step < 3600: # Run for a max of 1 hour simulation time
            self.run_step()
        traci.close()
        sys.stdout.flush()

if __name__ == "__main__":
    controller = TrafficController()
    controller.run()


