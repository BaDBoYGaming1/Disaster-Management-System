#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <thread>
#include <mutex>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <algorithm>
#include <cctype>

#pragma comment(lib, "ws2_32.lib")

using namespace std;

// Define constants at top
#define PORT 8080
#define BUFFER_SIZE 4096
#define MAX_CLIENTS 100

class Disaster {
public:
    int id;
    string type;
    string name;
    string location;
    string image_path;
    chrono::system_clock::time_point timestamp;
    
    Disaster(int id, string type, string name, string location, string image) 
        : id(id), type(type), name(name), location(location), image_path(image),
          timestamp(chrono::system_clock::now()) {}
    
    string to_json() const {
        return "{\"id\":" + to_string(id) + 
               ",\"type\":\"" + escape_json(type) + 
               "\",\"name\":\"" + escape_json(name) + 
               "\",\"location\":\"" + escape_json(location) + 
               "\",\"image\":\"" + escape_json(image_path) + 
               "\",\"timestamp\":" + to_string(chrono::duration_cast<chrono::seconds>(
                   timestamp.time_since_epoch()).count()) + "}";
    }
    
private:
    string escape_json(const string& s) const {
        string escaped;
        for (char c : s) {
            switch (c) {
                case '"': escaped += "\\\""; break;
                case '\\': escaped += "\\\\"; break;
                case '\n': escaped += "\\n"; break;
                case '\r': escaped += "\\r"; break;
                case '\t': escaped += "\\t"; break;
                default: escaped += c; break;
            }
        }
        return escaped;
    }
};

class Resource {
public:
    int id;
    string name;
    int quantity;
    int disaster_id;
    
    Resource(int id, string name, int quantity, int disaster_id) 
        : id(id), name(name), quantity(quantity), disaster_id(disaster_id) {}
    
    string to_json() const {
        return "{\"id\":" + to_string(id) + 
               ",\"name\":\"" + escape_json(name) + 
               "\",\"quantity\":" + to_string(quantity) + 
               ",\"disaster_id\":" + to_string(disaster_id) + "}";
    }
    
private:
    string escape_json(const string& s) const {
        string escaped;
        for (char c : s) {
            switch (c) {
                case '"': escaped += "\\\""; break;
                case '\\': escaped += "\\\\"; break;
                default: escaped += c; break;
            }
        }
        return escaped;
    }
};

class ClientSession {
public:
    SOCKET socket_fd;
    string username;
    string role;
    bool is_logged_in = false;
    
    ClientSession(SOCKET fd) : socket_fd(fd) {}
};

class DisasterManagementServer {
private:
    vector<Disaster> disasters;
    vector<Resource> resources;
    vector<ClientSession> clients;
    
    mutex data_mutex;
    int next_disaster_id = 1;
    int next_resource_id = 1;
    
    unordered_map<string, string> user_credentials = {
        {"admin", "admin123"},
        {"volunteer1", "vol123"},
        {"volunteer2", "vol456"}
    };
    
    unordered_map<string, string> user_roles = {
        {"admin", "admin"},
        {"volunteer1", "volunteer"},
        {"volunteer2", "volunteer"}
    };

public:
    DisasterManagementServer() {
        WSADATA wsaData;
        WSAStartup(MAKEWORD(2, 2), &wsaData);
        cout << "🚨 Disaster Management Server Initialized" << endl;
    }
    
    void delete_disaster(int disaster_id) {
    lock_guard<mutex> lock(data_mutex);

    disasters.erase(
        remove_if(disasters.begin(), disasters.end(),
            [disaster_id](const Disaster& d) { return d.id == disaster_id; }),
        disasters.end()
    );

    // Also delete related resources
    resources.erase(
        remove_if(resources.begin(), resources.end(),
            [disaster_id](const Resource& r) { return r.disaster_id == disaster_id; }),
        resources.end()
    );

    cout << "Deleted disaster ID: " << disaster_id << endl;
}

    ~DisasterManagementServer() {
        WSACleanup();
    }
    
    bool authenticate(const string& username, const string& password) {
        auto it = user_credentials.find(username);
        return it != user_credentials.end() && it->second == password;
    }
    
    string get_user_role(const string& username) {
        auto it = user_roles.find(username);
        if (it != user_roles.end()) {
            return it->second;
        }
        return "";
    }
    
    void add_disaster(const string& type, const string& name, 
                     const string& location, const string& image) {
        lock_guard<mutex> lock(data_mutex);
        disasters.emplace_back(next_disaster_id++, type, name, location, image);
        cout << "Added disaster: " << name << " (" << location << ")" << endl;
    }
    
    string get_all_disasters() {
        lock_guard<mutex> lock(data_mutex);
        string disasters_json = "[";
        bool first = true;
        for (const auto& disaster : disasters) {
            if (!first) disasters_json += ",";
            disasters_json += disaster.to_json();
            first = false;
        }
        disasters_json += "]";
        return disasters_json;
    }
    
    void add_resource(int disaster_id, const string& name, int quantity) {
        lock_guard<mutex> lock(data_mutex);
        resources.emplace_back(next_resource_id++, name, quantity, disaster_id);
        cout << "Added resource: " << name << " (qty: " << quantity << ") for disaster " << disaster_id << endl;
    }
    
    string get_resources_by_disaster(int disaster_id) {
        lock_guard<mutex> lock(data_mutex);
        string resources_json = "[";
        bool first = true;
        for (const auto& resource : resources) {
            if (resource.disaster_id == disaster_id) {
                if (!first) resources_json += ",";
                resources_json += resource.to_json();
                first = false;
            }
        }
        resources_json += "]";
        return resources_json;
    }
    
    void delete_resource(int resource_id) {
        lock_guard<mutex> lock(data_mutex);
        resources.erase(
            std::remove_if(resources.begin(), resources.end(),
                [resource_id](const Resource& r) { return r.id == resource_id; }),
            resources.end()
        );
        cout << "Deleted resource ID: " << resource_id << endl;
    }
    
    string get_route_url(const string& from_location, const string& to_location) {
        string encoded_from = url_encode(from_location);
        string encoded_to = url_encode(to_location);
        return "https://www.google.com/maps/dir/?api=1&origin=" + encoded_from + 
               "&destination=" + encoded_to + "&travelmode=driving";
    }
    
private:
    string url_encode(const string& value) {
        stringstream escaped;
        escaped.fill('0');
        escaped << hex;
        
        for (char c : value) {
            if (isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_' || c == '.' || c == '~') {
                escaped << c;
            } else {
                escaped << uppercase;
                escaped << '%' << setw(2) << int(static_cast<unsigned char>(c));
                escaped << nouppercase;
            }
        }
        return escaped.str();
    }
    
public:
    void handle_client(SOCKET client_socket) {
        char buffer[BUFFER_SIZE];
        
        try {
            while (true) {
                int bytes_received = recv(client_socket, buffer, BUFFER_SIZE - 1, 0);
                if (bytes_received <= 0) {
                    cout << "Client disconnected" << endl;
                    break;
                }
                
                buffer[bytes_received] = '\0';
                string request(buffer);
                
                string action = extract_json_value(request, "action");
                cout << "Received action: " << action << endl;
                
                string j_response;
                
                if (action == "login") {
                    string username = extract_json_value(request, "username");
                    string password = extract_json_value(request, "password");
                    
                    if (authenticate(username, password)) {
                        j_response = "{\"status\":\"success\",\"message\":\"Login successful\",\"data\":{\"role\":\"" + 
                                   get_user_role(username) + "\"}}";
                        cout << "User " << username << " logged in" << endl;
                    } else {
                        j_response = "{\"status\":\"error\",\"message\":\"Invalid credentials\"}";
                    }
                }
                else if (action == "add_disaster") {
                    string type = extract_json_value(request, "type");
                    string name = extract_json_value(request, "name");
                    string location = extract_json_value(request, "location");
                    string image = extract_json_value(request, "image", "");
                    
                    add_disaster(type, name, location, image);
                    j_response = "{\"status\":\"success\",\"message\":\"Disaster added successfully\"}";
                }
                else if (action == "delete_disaster") {
                try {
                    int disaster_id = stoi(extract_json_value(request, "disaster_id"));
                    delete_disaster(disaster_id);

                     j_response = "{\"status\":\"success\",\"message\":\"Disaster deleted\"}";
                    } 
                catch (...) {
                    j_response = "{\"status\":\"error\",\"message\":\"Invalid disaster ID\"}";
                    }
}
                else if (action == "get_disasters") {
                    j_response = "{\"status\":\"success\",\"message\":\"Disasters fetched\",\"data\":" + 
                               get_all_disasters() + "}";
                }
                else if (action == "get_route") {
                    string from_loc = extract_json_value(request, "from");
                    string to_loc = extract_json_value(request, "to");
                    
                    string route_url = get_route_url(from_loc, to_loc);
                    j_response = "{\"status\":\"success\",\"message\":\"Route generated\",\"data\":{\"url\":\"" + 
                               escape_json(route_url) + "\"}}";
                }
                else if (action == "add_resource") {
                    try {
                        int disaster_id = stoi(extract_json_value(request, "disaster_id"));
                        string name = extract_json_value(request, "name");
                        int quantity = stoi(extract_json_value(request, "quantity"));
                        
                        add_resource(disaster_id, name, quantity);
                        j_response = "{\"status\":\"success\",\"message\":\"Resource added\"}";
                    } catch (...) {
                        j_response = "{\"status\":\"error\",\"message\":\"Invalid resource data\"}";
                    }
                }
                else if (action == "get_resources") {
                    try {
                        int disaster_id = stoi(extract_json_value(request, "disaster_id"));
                        j_response = "{\"status\":\"success\",\"message\":\"Resources fetched\",\"data\":" + 
                                   get_resources_by_disaster(disaster_id) + "}";
                    } catch (...) {
                        j_response = "{\"status\":\"error\",\"message\":\"Invalid disaster ID\"}";
                    }
                }
                else if (action == "delete_resource") {
                    try {
                        int resource_id = stoi(extract_json_value(request, "resource_id"));
                        delete_resource(resource_id);
                        j_response = "{\"status\":\"success\",\"message\":\"Resource deleted\"}";
                    } catch (...) {
                        j_response = "{\"status\":\"error\",\"message\":\"Invalid resource ID\"}";
                    }
                }
                else {
                    j_response = "{\"status\":\"error\",\"message\":\"Unknown action: " + action + "\"}";
                }
                
                send(client_socket, j_response.c_str(), static_cast<int>(j_response.length()), 0);
            }
        } catch (exception& e) {
            cerr << "Error handling client: " << e.what() << endl;
        }
        
        closesocket(client_socket);
    }
    
    string extract_json_value(const string& json_str, const string& key, const string& default_val = "") {
        string search_key = "\"" + key + "\":";
        size_t key_pos = json_str.find(search_key);
        if (key_pos == string::npos) return default_val;
        
        size_t value_start = json_str.find(":", key_pos) + 1;
        if (value_start == string::npos) return default_val;
        
        // Skip whitespace
        while (value_start < json_str.length() && 
               (json_str[value_start] == ' ' || json_str[value_start] == '\t' || json_str[value_start] == '\n' || 
                json_str[value_start] == '\r')) {
            value_start++;
        }
        
        if (value_start >= json_str.length()) return default_val;
        
        if (json_str[value_start] == '"') {
            // String value
            size_t value_end = json_str.find("\"", value_start + 1);
            if (value_end == string::npos) return default_val;
            string result = json_str.substr(value_start + 1, value_end - value_start - 1);
            // Unescape JSON
            return unescape_json(result);
        } else {
            // Number value
            size_t value_end = value_start;
            while (value_end < json_str.length() && 
                   (isdigit(static_cast<unsigned char>(json_str[value_end])) || 
                    json_str[value_end] == '-' || json_str[value_end] == '.' || json_str[value_end] == 'e' || 
                    json_str[value_end] == 'E')) {
                value_end++;
            }
            return json_str.substr(value_start, value_end - value_start);
        }
    }
    
    string unescape_json(const string& s) {
        string result;
        for (size_t i = 0; i < s.length(); ++i) {
            if (s[i] == '\\' && i + 1 < s.length()) {
                switch (s[i + 1]) {
                    case '"': result += '"'; break;
                    case '\\': result += '\\'; break;
                    case 'n': result += '\n'; break;
                    case 'r': result += '\r'; break;
                    case 't': result += '\t'; break;
                    default: result += s[i + 1]; break;
                }
                ++i;
            } else {
                result += s[i];
            }
        }
        return result;
    }
    
    string escape_json(const string& s) {
        string escaped;
        for (char c : s) {
            switch (c) {
                case '"': escaped += "\\\""; break;
                case '\\': escaped += "\\\\"; break;
                case '\n': escaped += "\\n"; break;
                case '\r': escaped += "\\r"; break;
                case '\t': escaped += "\\t"; break;
                default: escaped += c; break;
            }
        }
        return escaped;
    }
    
    void start_server() {
        SOCKET server_fd;
        struct sockaddr_in address;
        int opt = 1;
        
        if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == INVALID_SOCKET) {
            cerr << "Socket failed: " << WSAGetLastError() << endl;
            exit(EXIT_FAILURE);
        }
        
        if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt)) == SOCKET_ERROR) {
            cerr << "setsockopt failed: " << WSAGetLastError() << endl;
            closesocket(server_fd);
            exit(EXIT_FAILURE);
        }
        
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(PORT);
        
        if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) == SOCKET_ERROR) {
            cerr << "Bind failed: " << WSAGetLastError() << endl;
            closesocket(server_fd);
            exit(EXIT_FAILURE);
        }
        
        if (listen(server_fd, 10) == SOCKET_ERROR) {
            cerr << "Listen failed: " << WSAGetLastError() << endl;
            closesocket(server_fd);
            exit(EXIT_FAILURE);
        }
        
        cout << "🚨 Disaster Management Server running on port " << PORT << endl;
        cout << "📱 Admin: admin/admin123" << endl;
        cout << "👥 Volunteer: volunteer1/vol123, volunteer2/vol456" << endl;
        cout << "Press Ctrl+C to stop" << endl;
        
        while (true) {
            SOCKET client_socket;
            struct sockaddr_in client_addr;
            int client_len = sizeof(client_addr);
            
            client_socket = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);
            if (client_socket == INVALID_SOCKET) {
                cerr << "Accept failed: " << WSAGetLastError() << endl;
                continue;
            }
            
            cout << "New client connected!" << endl;
            thread client_thread(&DisasterManagementServer::handle_client, this, client_socket);
            client_thread.detach();
        }
        
        closesocket(server_fd);
    }
};

int main() {
    try {
        DisasterManagementServer server;
        server.start_server();
    } catch (exception& e) {
        cerr << "Server error: " << e.what() << endl;
        WSACleanup();
        return 1;
    }
    return 0;
}