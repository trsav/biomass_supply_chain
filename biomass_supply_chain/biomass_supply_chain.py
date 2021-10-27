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


def place_nodes(nodes):
    """
    Places nodes randomly on a sphere,
    returns degrees and NOT radians
    """
    locations = rnd.uniform([-180, -90], [180, 90], (nodes, 2))
    return locations


def place_node_set(nodes_set):
    """
    Takes a list of node set sizes and returns a list of their locations
    """
    node_locations = []
    for nodes in nodes_set:
        node_locations.append(place_nodes(nodes))
    return node_locations


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


def calculate_distances(node_set_1, node_set_2):
    """
    Calculates the distance between two sets of nodes on a sphere.
    Returns corresponding matrix of distances.
    Distances are in km.
    """
    num_1 = len(node_set_1)
    num_2 = len(node_set_2)
    distance_matrix = np.zeros((num_1, num_2))
    factor = np.pi / 180.0
    for i in range(num_1):
        rad_1 = node_set_1[i, :] * factor
        for j in range(num_2):
            rad_2 = node_set_2[j, :] * factor
            distance_matrix[i, j] = distance_on_sphere(rad_1, rad_2)
    return distance_matrix


def get_random_parameters(amount, limit):
    return rnd.uniform(0, limit, (amount, 1))


def build_problem(production_nodes, processing_nodes, demand_nodes):

    [production_locations, processing_locations, demand_locations] = place_node_set(
        [production_nodes, processing_nodes, demand_nodes]
    )
    # calculating distances
    production_distance_matrix = calculate_distances(
        production_locations, processing_locations
    )
    demand_distance_matrix = calculate_distances(processing_locations, demand_locations)
    # defining demand values
    demand_amounts = get_random_parameters(demand_nodes, 1)
    # defining production limits that still result in a feasible problem
    production_limits = get_random_parameters(production_nodes, 5)
    # defining cost of production at each production node
    production_cost = get_random_parameters(production_nodes, 2)
    # defining processing limits
    processing_limits = get_random_parameters(processing_nodes, 10)
    # defining processing cost at each processing node
    processing_cost = get_random_parameters(processing_nodes, 1)

    m = ConcreteModel()
    cost = 0
    m.production_vars = Var(
        range(production_nodes), range(processing_nodes), domain=NonNegativeReals
    )
    m.distribution_vars = Var(
        range(processing_nodes), range(demand_nodes), domain=NonNegativeReals
    )
    m.production_constraints = ConstraintList()
    for i in range(production_nodes):
        # Production limit constraint of each production node
        limit = sum(m.production_vars[i, :]) <= production_limits[i, 0]
        m.production_constraints.add(expr=limit)
        # Adding production cost of each production node to cost
        cost += sum(m.production_vars[i, :]) * production_cost[i, 0]
        for j in range(processing_nodes):
            # Adding cost of transport to each processing node per production node
            cost += m.production_vars[i, j] * production_distance_matrix[i, j]

    m.processing_constraints = ConstraintList()
    for i in range(processing_nodes):
        # Adding limit on processing amount per processing node
        m.processing_constraints.add(
            expr=sum(m.distribution_vars[i, :]) <= processing_limits[i, 0]
        )
        # Adding mass balance on each processing node
        m.processing_constraints.add(
            expr=sum(m.distribution_vars[i, :]) == sum(m.production_vars[:, i])
        )
        # Adding cost of processing to cost function
        cost += sum(m.distribution_vars[i, :]) * processing_cost[i, 0]
        # Adding cost of transport to each demand node per production node
        for j in range(demand_nodes):
            cost += m.distribution_vars[i, j] * demand_distance_matrix[i, j]
    # Adding minimum demand fulfilment for each demand node
    m.demand_constraints = ConstraintList()
    for i in range(demand_nodes):
        m.processing_constraints.add(
            expr=sum(m.distribution_vars[:, i]) >= demand_amounts[i, 0]
        )
    m.objective = Objective(expr=cost, sense=minimize)
    dict = {}
    dict["model"] = m
    dict["production_locations"] = production_locations
    dict["processing_locations"] = processing_locations
    dict["demand_locations"] = demand_locations
    return dict


def plot_nodes(ax, nodes, name, color):
    ax.scatter(
        nodes[:, 0],
        nodes[:, 1],
        transform=ccrs.Geodetic(),
        color=color,
        s=20,
        alpha=0.5,
        zorder=1,
        label=name,
    )
    return


def plot_transport(ax, matrix, loc1, loc2, color):
    for i in range(len(loc1)):
        for j in range(len(loc2)):
            ax.plot(
                [loc1[i, 0], loc2[j, 0]],
                [loc1[i, 1], loc2[j, 1]],
                transform=ccrs.Geodetic(),
                color=color,
                alpha=0.5,
                linewidth=matrix[i, j] * 1,
                zorder=-1,
            )
    return


def plot_solution(
    production_locations,
    processing_locations,
    demand_locations,
    processing_vars,
    demand_vars,
):
    fig = plt.figure(figsize=(9, 5))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    ax.set_global()
    ax.gridlines(alpha=0.5)
    plot_transport(
        ax, processing_vars, production_locations, processing_locations, "green"
    )
    plot_transport(ax, demand_vars, processing_locations, demand_locations, "tab:blue")
    plot_nodes(ax, production_locations, "Production", "green")
    plot_nodes(ax, processing_locations, "Processing", "tab:blue")
    plot_nodes(ax, demand_locations, "Demand", "k")

    type_legend = plt.legend(loc="lower left")
    for i in range(len(type_legend.legendHandles)):
        type_legend.legendHandles[i]._sizes = [30]
    plt.show()
    return


production_nodes = 20
processing_nodes = 10
demand_nodes = 50

problem = build_problem(production_nodes, processing_nodes, demand_nodes)
results = SolverFactory("ipopt").solve(problem["model"])
results.write()

production_vars = (
    np.array(problem["model"].production_vars[:, :]())
    .reshape((production_nodes, processing_nodes))
    .clip(min=0)
)
distribution_vars = (
    np.array(problem["model"].distribution_vars[:, :]())
    .reshape((processing_nodes, demand_nodes))
    .clip(min=0)
)

plot_solution(
    problem["production_locations"],
    problem["processing_locations"],
    problem["demand_locations"],
    production_vars,
    distribution_vars,
)
