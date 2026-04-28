/*
 * Disaster Management Relief System - Core Engine
 * Backend: C
 * Features: Dijkstra's shortest path, disaster/resource management,
 *           distance calculations using Haversine formula
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_NODES       100
#define MAX_DISASTERS   50
#define MAX_RESOURCES   100
#define MAX_USERS       200
#define INF             1e9
#define PI              3.14159265358979323846
#define EARTH_RADIUS_KM 6371.0

/* ─── Data Structures ─── */

typedef struct {
    int   id;
    char  name[64];
    char  type[32];       /* flood, earthquake, fire, cyclone, etc. */
    double lat;
    double lon;
    int   severity;       /* 1-5 */
    char  status[16];     /* active, resolved, monitoring */
    char  created_at[32];
} Disaster;

typedef struct {
    int   id;
    char  name[64];
    char  type[32];       /* medical, food, shelter, rescue_team, etc. */
    double lat;
    double lon;
    int   quantity;
    char  unit[16];
    int   disaster_id;    /* 0 = unassigned */
    char  status[16];     /* available, deployed, exhausted */
} Resource;

typedef struct {
    int   id;
    char  username[32];
    char  password_hash[64]; /* simple SHA-like placeholder */
    char  role[16];          /* admin, responder, viewer */
    char  email[64];
    double last_lat;
    double last_lon;
} User;

typedef struct {
    double dist[MAX_NODES][MAX_NODES];
    int    node_count;
    char   node_names[MAX_NODES][64];
    double node_lat[MAX_NODES];
    double node_lon[MAX_NODES];
} Graph;

typedef struct {
    double distance_km;
    int    path[MAX_NODES];
    int    path_len;
    double waypoint_lats[MAX_NODES];
    double waypoint_lons[MAX_NODES];
} RouteResult;

/* ─── Global State ─── */
static Disaster  disasters[MAX_DISASTERS];
static Resource  resources[MAX_RESOURCES];
static User      users[MAX_USERS];
static Graph     graph;
static int       disaster_count = 0;
static int       resource_count = 0;
static int       user_count     = 0;
static int       next_disaster_id = 1;
static int       next_resource_id = 1;
static int       next_user_id     = 1;

/* ─── Utility Functions ─── */

double deg_to_rad(double deg) {
    return deg * PI / 180.0;
}

/* Haversine formula: great-circle distance between two lat/lon points */
double haversine_distance(double lat1, double lon1, double lat2, double lon2) {
    double dlat = deg_to_rad(lat2 - lat1);
    double dlon = deg_to_rad(lon2 - lon1);
    double a = sin(dlat/2) * sin(dlat/2)
             + cos(deg_to_rad(lat1)) * cos(deg_to_rad(lat2))
             * sin(dlon/2) * sin(dlon/2);
    double c = 2 * atan2(sqrt(a), sqrt(1-a));
    return EARTH_RADIUS_KM * c;
}

/* Simple string hash for passwords (NOT production-grade) */
void simple_hash(const char *input, char *output) {
    unsigned long hash = 5381;
    int c;
    while ((c = (unsigned char)*input++))
        hash = ((hash << 5) + hash) + c;
    sprintf(output, "%lu", hash);
}

void get_timestamp(char *buf, int len) {
    time_t t = time(NULL);
    struct tm *tm_info = localtime(&t);
    strftime(buf, len, "%Y-%m-%d %H:%M:%S", tm_info);
}

/* ─── User Management ─── */

int user_register(const char *username, const char *password,
                  const char *role, const char *email) {
    if (user_count >= MAX_USERS) return -1;
    /* Check duplicate */
    for (int i = 0; i < user_count; i++)
        if (strcmp(users[i].username, username) == 0) return -2;

    User *u = &users[user_count];
    u->id = next_user_id++;
    strncpy(u->username, username, sizeof(u->username)-1);
    strncpy(u->role,     role,     sizeof(u->role)-1);
    strncpy(u->email,    email,    sizeof(u->email)-1);
    simple_hash(password, u->password_hash);
    u->last_lat = 0.0;
    u->last_lon = 0.0;
    user_count++;
    return u->id;
}

int user_login(const char *username, const char *password) {
    char hash[64];
    simple_hash(password, hash);
    for (int i = 0; i < user_count; i++) {
        if (strcmp(users[i].username, username) == 0 &&
            strcmp(users[i].password_hash, hash) == 0)
            return users[i].id;
    }
    return -1;
}

User* user_get_by_id(int id) {
    for (int i = 0; i < user_count; i++)
        if (users[i].id == id) return &users[i];
    return NULL;
}

void user_update_location(int user_id, double lat, double lon) {
    User *u = user_get_by_id(user_id);
    if (u) { u->last_lat = lat; u->last_lon = lon; }
}

/* ─── Disaster Management ─── */

int disaster_add(const char *name, const char *type,
                 double lat, double lon, int severity) {
    if (disaster_count >= MAX_DISASTERS) return -1;
    Disaster *d = &disasters[disaster_count];
    d->id = next_disaster_id++;
    strncpy(d->name, name, sizeof(d->name)-1);
    strncpy(d->type, type, sizeof(d->type)-1);
    d->lat      = lat;
    d->lon      = lon;
    d->severity = severity;
    strcpy(d->status, "active");
    get_timestamp(d->created_at, sizeof(d->created_at));
    disaster_count++;
    return d->id;
}

int disaster_remove(int disaster_id) {
    for (int i = 0; i < disaster_count; i++) {
        if (disasters[i].id == disaster_id) {
            strcpy(disasters[i].status, "resolved");
            return 0;
        }
    }
    return -1;
}

int disaster_update_status(int disaster_id, const char *status) {
    for (int i = 0; i < disaster_count; i++) {
        if (disasters[i].id == disaster_id) {
            strncpy(disasters[i].status, status, sizeof(disasters[i].status)-1);
            return 0;
        }
    }
    return -1;
}

Disaster* disaster_get_by_id(int id) {
    for (int i = 0; i < disaster_count; i++)
        if (disasters[i].id == id) return &disasters[i];
    return NULL;
}

/* ─── Resource Management ─── */

int resource_add(const char *name, const char *type,
                 double lat, double lon,
                 int quantity, const char *unit) {
    if (resource_count >= MAX_RESOURCES) return -1;
    Resource *r = &resources[resource_count];
    r->id = next_resource_id++;
    strncpy(r->name, name, sizeof(r->name)-1);
    strncpy(r->type, type, sizeof(r->type)-1);
    strncpy(r->unit, unit, sizeof(r->unit)-1);
    r->lat         = lat;
    r->lon         = lon;
    r->quantity    = quantity;
    r->disaster_id = 0;
    strcpy(r->status, "available");
    resource_count++;
    return r->id;
}

int resource_remove(int resource_id) {
    for (int i = 0; i < resource_count; i++) {
        if (resources[i].id == resource_id) {
            strcpy(resources[i].status, "exhausted");
            return 0;
        }
    }
    return -1;
}

int resource_assign(int resource_id, int disaster_id) {
    for (int i = 0; i < resource_count; i++) {
        if (resources[i].id == resource_id) {
            resources[i].disaster_id = disaster_id;
            strcpy(resources[i].status, "deployed");
            return 0;
        }
    }
    return -1;
}

/* ─── Dijkstra's Algorithm ─── */

void graph_init(void) {
    for (int i = 0; i < MAX_NODES; i++)
        for (int j = 0; j < MAX_NODES; j++)
            graph.dist[i][j] = (i == j) ? 0.0 : INF;
    graph.node_count = 0;
}

int graph_add_node(const char *name, double lat, double lon) {
    int idx = graph.node_count++;
    strncpy(graph.node_names[idx], name, 63);
    graph.node_lat[idx] = lat;
    graph.node_lon[idx] = lon;
    /* Auto-connect to all existing nodes with Haversine distance */
    for (int i = 0; i < idx; i++) {
        double d = haversine_distance(lat, lon,
                                      graph.node_lat[i],
                                      graph.node_lon[i]);
        graph.dist[idx][i] = d;
        graph.dist[i][idx] = d;
    }
    return idx;
}

RouteResult dijkstra(int src, int dest) {
    RouteResult result;
    result.distance_km = INF;
    result.path_len    = 0;

    int   n = graph.node_count;
    double dist[MAX_NODES];
    int    prev[MAX_NODES];
    int    visited[MAX_NODES];

    for (int i = 0; i < n; i++) {
        dist[i]    = INF;
        prev[i]    = -1;
        visited[i] = 0;
    }
    dist[src] = 0.0;

    for (int iter = 0; iter < n; iter++) {
        /* Find unvisited node with minimum distance */
        int u = -1;
        for (int i = 0; i < n; i++)
            if (!visited[i] && (u == -1 || dist[i] < dist[u]))
                u = i;
        if (u == -1 || dist[u] == INF) break;
        visited[u] = 1;
        if (u == dest) break;

        for (int v = 0; v < n; v++) {
            if (!visited[v] && graph.dist[u][v] < INF) {
                double alt = dist[u] + graph.dist[u][v];
                if (alt < dist[v]) {
                    dist[v] = alt;
                    prev[v] = u;
                }
            }
        }
    }

    result.distance_km = dist[dest];

    /* Reconstruct path */
    int path_rev[MAX_NODES];
    int len = 0;
    for (int at = dest; at != -1; at = prev[at])
        path_rev[len++] = at;

    for (int i = 0; i < len; i++) {
        result.path[i]          = path_rev[len-1-i];
        result.waypoint_lats[i] = graph.node_lat[path_rev[len-1-i]];
        result.waypoint_lons[i] = graph.node_lon[path_rev[len-1-i]];
    }
    result.path_len = len;
    return result;
}

/* Find nearest active disaster to a given location */
int find_nearest_disaster(double user_lat, double user_lon,
                          double *out_distance) {
    int    nearest_id   = -1;
    double min_dist     = INF;

    for (int i = 0; i < disaster_count; i++) {
        if (strcmp(disasters[i].status, "active") != 0) continue;
        double d = haversine_distance(user_lat, user_lon,
                                      disasters[i].lat,
                                      disasters[i].lon);
        if (d < min_dist) {
            min_dist   = d;
            nearest_id = disasters[i].id;
        }
    }
    if (out_distance) *out_distance = min_dist;
    return nearest_id;
}

/* Find nearest available resource to a disaster */
int find_nearest_resource(int disaster_id, const char *resource_type,
                          double *out_distance) {
    Disaster *d = disaster_get_by_id(disaster_id);
    if (!d) return -1;

    int    nearest_id = -1;
    double min_dist   = INF;

    for (int i = 0; i < resource_count; i++) {
        if (strcmp(resources[i].status, "available") != 0) continue;
        if (resource_type && strlen(resource_type) > 0 &&
            strcmp(resources[i].type, resource_type) != 0) continue;
        double dist = haversine_distance(d->lat, d->lon,
                                         resources[i].lat, resources[i].lon);
        if (dist < min_dist) {
            min_dist   = dist;
            nearest_id = resources[i].id;
        }
    }
    if (out_distance) *out_distance = min_dist;
    return nearest_id;
}

/* ─── JSON Serialisation helpers ─── */

void json_disasters(char *buf, int buf_size) {
    int pos = 0;
    pos += snprintf(buf+pos, buf_size-pos, "[");
    int first = 1;
    for (int i = 0; i < disaster_count; i++) {
        Disaster *d = &disasters[i];
        if (!first) pos += snprintf(buf+pos, buf_size-pos, ",");
        pos += snprintf(buf+pos, buf_size-pos,
            "{\"id\":%d,\"name\":\"%s\",\"type\":\"%s\","
            "\"lat\":%.6f,\"lon\":%.6f,\"severity\":%d,"
            "\"status\":\"%s\",\"created_at\":\"%s\"}",
            d->id, d->name, d->type,
            d->lat, d->lon, d->severity,
            d->status, d->created_at);
        first = 0;
    }
    snprintf(buf+pos, buf_size-pos, "]");
}

void json_resources(char *buf, int buf_size) {
    int pos = 0;
    pos += snprintf(buf+pos, buf_size-pos, "[");
    int first = 1;
    for (int i = 0; i < resource_count; i++) {
        Resource *r = &resources[i];
        if (!first) pos += snprintf(buf+pos, buf_size-pos, ",");
        pos += snprintf(buf+pos, buf_size-pos,
            "{\"id\":%d,\"name\":\"%s\",\"type\":\"%s\","
            "\"lat\":%.6f,\"lon\":%.6f,\"quantity\":%d,"
            "\"unit\":\"%s\",\"disaster_id\":%d,\"status\":\"%s\"}",
            r->id, r->name, r->type,
            r->lat, r->lon, r->quantity,
            r->unit, r->disaster_id, r->status);
        first = 0;
    }
    snprintf(buf+pos, buf_size-pos, "]");
}

/* ─── C Shared Library API (called by Python via ctypes) ─── */

/* Init with seed data */
void engine_init(void) {
    graph_init();

    /* Seed admin user */
    user_register("admin", "admin123", "admin", "admin@relief.org");
    user_register("responder1", "resp123", "responder", "r1@relief.org");

    /* Seed sample disasters (India-centric coordinates) */
    disaster_add("Kerala Flood Zone",   "flood",      10.8505,  76.2711, 5);
    disaster_add("Odisha Cyclone Belt", "cyclone",    20.9517,  85.0985, 4);
    disaster_add("Uttarakhand Landslide","landslide", 30.0668,  79.0193, 3);
    disaster_add("Delhi Heatwave",      "heatwave",   28.6139,  77.2090, 2);

    /* Seed resources */
    resource_add("NDRF Team Alpha",   "rescue_team", 19.0760, 72.8777, 50, "personnel");
    resource_add("Medical Camp Beta", "medical",     13.0827, 80.2707, 200,"kits");
    resource_add("Food Relief Depot", "food",        22.5726, 88.3639, 1000,"packets");
    resource_add("Shelter Units",     "shelter",     17.3850, 78.4867, 300,"tents");

    /* Build graph nodes */
    graph_add_node("Mumbai",    19.0760, 72.8777);
    graph_add_node("Chennai",   13.0827, 80.2707);
    graph_add_node("Kolkata",   22.5726, 88.3639);
    graph_add_node("Hyderabad", 17.3850, 78.4867);
    graph_add_node("Delhi",     28.6139, 77.2090);
    graph_add_node("Kochi",     9.9312,  76.2673);
    graph_add_node("Bhubaneswar",20.2961,85.8189);
    graph_add_node("Dehradun",  30.3165, 78.0322);
}

int engine_add_disaster(const char *name, const char *type,
                        double lat, double lon,
                        int severity) {
    return disaster_add(name, type, lat, lon, severity);
}

int engine_remove_disaster(int id)          { return disaster_remove(id); }

int engine_add_resource(const char *name, const char *type,
                        double lat, double lon,
                        int qty, const char *unit) {
    return resource_add(name, type, lat, lon, qty, unit);
}

int engine_remove_resource(int id)          { return resource_remove(id); }
int engine_assign_resource(int rid, int did){ return resource_assign(rid, did); }

int engine_login(const char *user, const char *pass) {
    return user_login(user, pass);
}

int engine_register(const char *user, const char *pass,
                    const char *role, const char *email) {
    return user_register(user, pass, role, email);
}

void engine_update_location(int uid, double lat, double lon) {
    user_update_location(uid, lat, lon);
}

/* Returns JSON strings into caller-supplied buffers */
void engine_get_disasters(char *buf, int size) { json_disasters(buf, size); }
void engine_get_resources(char *buf, int size) { json_resources(buf, size); }

/* Distance + nearest disaster JSON */
void engine_nearest_disaster(double lat, double lon, char *buf, int size) {
    double dist;
    int id = find_nearest_disaster(lat, lon, &dist);
    if (id < 0) {
        snprintf(buf, size, "{\"found\":false}");
        return;
    }
    Disaster *d = disaster_get_by_id(id);
    /* Build Google Maps directions URL */
    snprintf(buf, size,
        "{\"found\":true,\"id\":%d,\"name\":\"%s\","
        "\"type\":\"%s\",\"severity\":%d,"
        "\"lat\":%.6f,\"lon\":%.6f,"
        "\"distance_km\":%.2f,"
        "\"maps_url\":\"https://www.google.com/maps/dir/%.6f,%.6f/%.6f,%.6f\","
        "\"osm_url\":\"https://www.openstreetmap.org/directions?from=%.6f%%2C%.6f&to=%.6f%%2C%.6f\"}",
        d->id, d->name, d->type, d->severity,
        d->lat, d->lon, dist,
        lat, lon, d->lat, d->lon,
        lat, lon, d->lat, d->lon);
}

/* Route between two node indices using Dijkstra */
void engine_route(int src_node, int dst_node, char *buf, int size) {
    RouteResult r = dijkstra(src_node, dst_node);
    int pos = snprintf(buf, size,
        "{\"distance_km\":%.2f,\"waypoints\":[", r.distance_km);
    for (int i = 0; i < r.path_len && pos < size-50; i++) {
        if (i) pos += snprintf(buf+pos, size-pos, ",");
        pos += snprintf(buf+pos, size-pos,
            "{\"name\":\"%s\",\"lat\":%.6f,\"lon\":%.6f}",
            graph.node_names[r.path[i]],
            r.waypoint_lats[i], r.waypoint_lons[i]);
    }
    snprintf(buf+pos, size-pos, "]}");
}

/* Stats summary */
void engine_stats(char *buf, int size) {
    int active=0, resolved=0, total_res=0, deployed_res=0;
    for (int i=0;i<disaster_count;i++){
        if(strcmp(disasters[i].status,"active")==0) active++;
        else resolved++;
    }
    for (int i=0;i<resource_count;i++){
        total_res++;
        if(strcmp(resources[i].status,"deployed")==0) deployed_res++;
    }
    snprintf(buf, size,
        "{\"active_disasters\":%d,\"resolved_disasters\":%d,"
        "\"total_resources\":%d,\"deployed_resources\":%d,"
        "\"total_users\":%d}",
        active, resolved, total_res, deployed_res, user_count);
}

/* Get user role */
void engine_user_info(int uid, char *buf, int size) {
    User *u = user_get_by_id(uid);
    if (!u) { snprintf(buf, size, "{\"found\":false}"); return; }
    snprintf(buf, size,
        "{\"found\":true,\"id\":%d,\"username\":\"%s\","
        "\"role\":\"%s\",\"email\":\"%s\"}",
        u->id, u->username, u->role, u->email);
}
