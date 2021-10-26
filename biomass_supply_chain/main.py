import numpy as np
import matplotlib.pyplot as plt
import numpy.random as rnd
import cartopy.crs as ccrs
from pyomo.environ import (
    Var,
    NonNegativeReals,
    ConcreteModel,
    ConstraintList,
    Objective,
    minimize,
    SolverFactory,
)

rnd.seed(100000)


def place_nodes(supply_nodes, demand_nodes):
    """
    Places supply and demand nodes randomly on a sphere,
    returns degrees and NOT radians
    """
    total_nodes = supply_nodes + demand_nodes
    locations = rnd.uniform([-180, -90], [180, 90], (total_nodes, 2))
    supply_locations = locations[:supply_nodes, :]
    demand_locations = locations[supply_nodes:, :]
    return supply_locations, demand_locations


def distance_on_sphere(point1, point2):
    """
    Calculates the distance between two coordinates on a sphere (in radians)
    In this case Earth.
    point1: [Lon,Lat]
    point2: [Lon,Lat]
    """
    earth_r = 6371
    delta = point2 - point1
    a = (
        np.sin(delta[1] / 2) ** 2
        + np.cos(point1[1]) * np.cos(point2[1]) * np.sin(delta[0] / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance = earth_r * c
    return distance


def calculate_distances(supply_locations, demand_locations):
    """
    Calculates the distance between supply and demand nodes on a sphere
    and returns corresponding matrix.
    Distances are in km.
    """
    num_supply = len(supply_locations)
    num_demand = len(demand_locations)
    distance_matrix = np.zeros((num_supply, num_demand))
    factor = np.pi / 180.0
    for i in range(num_supply):
        rad_supply = supply_locations[i, :] * factor
        for j in range(num_demand):
            rad_demand = demand_locations[j, :] * factor
            distance_matrix[i, j] = distance_on_sphere(rad_supply, rad_demand)
    return distance_matrix


def plot_nodes(
    supply_locations, demand_locations, demand_amounts, supply_limits, supply_vars
):
    """
    Given the location of supply and demand nodes,
    plots them and their connections on a projection.
    """
    fig = plt.figure(figsize=(9, 5))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    ax.set_global()
    for i in range(len(supply_locations)):
        for j in range(len(demand_locations)):
            ax.plot(
                [supply_locations[i, 0], demand_locations[j, 0]],
                [supply_locations[i, 1], demand_locations[j, 1]],
                transform=ccrs.Geodetic(),
                color="k",
                alpha=0.25,
                linewidth=supply_vars[i, j] * 10,
                zorder=-1,
            )
    ax.gridlines(alpha=0.5)
    ax.scatter(
        supply_locations[:, 0],
        supply_locations[:, 1],
        transform=ccrs.Geodetic(),
        color="white",
        edgecolors="k",
        linestyle="dashed",
        s=supply_limits[:, 0] * 100,
        zorder=1,
        label="Production Limits",
    )
    supply_sum = np.sum(supply_vars, axis=1)
    ax.scatter(
        supply_locations[:, 0],
        supply_locations[:, 1],
        transform=ccrs.Geodetic(),
        color="k",
        edgecolors="k",
        linestyle="dashed",
        s=supply_sum[:] * 100,
        zorder=1,
        label="Actual Production",
    )

    demand_color = "tab:blue"
    dm = ax.scatter(
        demand_locations[:, 0],
        demand_locations[:, 1],
        transform=ccrs.Geodetic(),
        color=demand_color,
        s=demand_amounts[:, 0] * 100,
        zorder=1,
        label="Demand",
    )
    type_legend = plt.legend(loc="upper left")
    kw = dict(prop="sizes", num=5, color="k", alpha=0.5, func=lambda s: s / 100)
    plt.legend(*dm.legend_elements(**kw), title="Quantity", loc="lower left")
    ax.add_artist(type_legend)
    type_legend.legendHandles[0]._sizes = [50]
    type_legend.legendHandles[1]._sizes = [50]
    plt.show()
    return


def get_demand_amounts(demand_nodes):
    demand_limit = 1
    return np.random.uniform(0, demand_limit, (demand_nodes, 1))


def get_production_costs(supply_nodes):
    cost_limit = 1
    return np.random.uniform(0, cost_limit, (supply_nodes, 1))


def get_supply_limits(demand_amounts, supply_nodes):
    full_demand = sum(demand_amounts)
    supply_flexibility = 0.5
    demand_nodes = len(demand_amounts)
    supply_limits = np.random.uniform(
        (full_demand / supply_nodes),
        (full_demand / supply_nodes) + supply_flexibility * demand_nodes,
        (supply_nodes, 1),
    )
    return supply_limits


def build_problem(supply_nodes, demand_nodes):
    supply_locations, demand_locations = place_nodes(supply_nodes, demand_nodes)
    # calculating distances
    distance_matrix = calculate_distances(supply_locations, demand_locations)
    # defining demand values
    demand_amounts = get_demand_amounts(demand_nodes)
    # defining supply limits that still result in a feasible problem
    supply_limits = get_supply_limits(demand_amounts, supply_nodes)
    # defining cost of production at each supply node
    production_cost = get_production_costs(supply_nodes)

    m = ConcreteModel()
    cost = 0
    m.supply_vars = Var(
        range(supply_nodes), range(demand_nodes), domain=NonNegativeReals
    )
    m.production_constraints = ConstraintList()
    for i in range(supply_nodes):
        limit = sum(m.supply_vars[i, :]) <= supply_limits[i, 0]
        m.production_constraints.add(expr=limit)
        for j in range(demand_nodes):
            cost += m.supply_vars[i, j] * distance_matrix[i, j] * production_cost[i, 0]
    m.demand_constraints = ConstraintList()
    for i in range(demand_nodes):
        demand_constraint = sum(m.supply_vars[:, i]) >= demand_amounts[i, 0]
        m.demand_constraints.add(expr=demand_constraint)
    m.objective = Objective(expr=cost, sense=minimize)
    dict = {}
    dict["model"] = m
    dict["supply_locations"] = supply_locations
    dict["demand_locations"] = demand_locations
    dict["demand_amounts"] = demand_amounts
    dict["supply_limits"] = supply_limits
    return dict


supply_nodes = 10
demand_nodes = 50
problem = build_problem(supply_nodes, demand_nodes)
results = SolverFactory("ipopt").solve(problem["model"])
results.write()
supply_vars = (
    np.array(problem["model"].supply_vars[:, :]())
    .reshape((supply_nodes, demand_nodes))
    .clip(min=0)
)

# plotting nodes
plot_nodes(
    problem["supply_locations"],
    problem["demand_locations"],
    problem["demand_amounts"],
    problem["supply_limits"],
    supply_vars,
)
