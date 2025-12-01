import logging
from erc3 import erc3 as dev, store, ApiException
from smolagents import Tool

CLI_RED = "\x1b[31m"
CLI_GREEN = "\x1b[32m"
CLI_CLR = "\x1b[0m"

functions = [
        dev.Req_GetCustomer, # "/customers/get"
        dev.Req_GetEmployee, # "/employees/get"
        dev.Req_GetProject, # "/projects/get"
        dev.Req_GetTimeEntry, # "/time/get"
        dev.Req_ListCustomers, # "/customers/list"
        dev.Req_ListEmployees, # "/employees/list"
        dev.Req_ListProjects, # "/projects/list"
        dev.Req_ListWiki, # "/wiki/list"
        dev.Req_LoadWiki, # "/wiki/load"
        dev.Req_LogTimeEntry, #  "/time/log"
        dev.Req_ProvideAgentResponse, #"/respond"
        dev.Req_SearchCustomers, # "/customers/search"
        dev.Req_SearchEmployees, #"/employees/search"
        dev.Req_SearchProjects, # "/projects/search"
        dev.Req_SearchTimeEntries, # "/time/search"
        dev.Req_SearchWiki, # "/wiki/search"
        dev.Req_TimeSummaryByEmployee, # "/time/summary/by-employee"
        dev.Req_TimeSummaryByProject, # "/time/summary/by-project"
        dev.Req_UpdateEmployeeInfo, # "/employees/update"
        dev.Req_UpdateProjectStatus, # "/projects/status/update"
        dev.Req_UpdateProjectTeam, # "/projects/team/update"
        dev.Req_UpdateTimeEntry, # "/time/update"
        dev.Req_UpdateWiki, # "/wiki/update"
        dev.Req_WhoAmI, # "/whoami"


    ]

class StoreAPITool(Tool):
    """Base class for store API tools"""

    def __init__(self):
        # Initialize Tool with proper attributes - subclasses will set specific values
        super().__init__()

    def _execute_api_call(self, **kwargs) -> str:
        # Log tool invocation
        logging.info(f"{CLI_GREEN}[TOOL]{CLI_CLR} {self.name} called with: {kwargs}")

        try:
            # Create request object from kwargs
            request = self.request_class(**kwargs)
            logging.info(f"{CLI_GREEN}[REQUEST]{CLI_CLR} {type(request)} -> {request}")

            if request is not None:
                if isinstance(request, dict):
                    logging.info(
                        f"{CLI_GREEN}[API]{CLI_CLR} Executing {self.request_class.__name__}: {request}"
                    )
                else:
                    logging.info(
                        f"{CLI_GREEN}[API]{CLI_CLR} Executing {self.request_class.__name__}: {request.model_dump()}"
                    )

            # Execute the API call
            result = self.store_api.dispatch(request)

            # Handle case where API returns None
            if result is not None:
                # Handle both Pydantic models and plain dicts
                if isinstance(result, dict):
                    import json

                    result_json = json.dumps(result)
                else:
                    result_json = result.model_dump_json(
                        exclude_none=True, exclude_unset=True
                    )

                logging.info(
                    f"{CLI_GREEN}[RESULT]{CLI_CLR} {self.name} -> {result_json}"
                )

                return result_json
            else:
                logging.info(f"{CLI_GREEN}[RESULT]{CLI_CLR} {self.name} -> No content")
                return "No content"
        except ApiException as e:
            error_msg = f"API Error: {e.api_error.error}"
            logging.info(f"{CLI_RED}[ERROR]{CLI_CLR} {self.name} -> {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logging.info(f"{CLI_RED}[ERROR]{CLI_CLR} {self.name} -> {error_msg}")
            return error_msg


class ProvideAgentResponseTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "provide_agent_response"
        self.description = "Provide a response to the user. Required parameters: message (str), outcome (str). Optional: links (list)"
        # LinkKind reference from dtos.py: Literal["employee", "customer", "project", "wiki", "location"]
        self.inputs = {
            "message": {"type": "string", "description": "The response message to provide to the user"},
            "outcome": {"type": "string", "description": "The outcome type: ok_answer, ok_not_found, denied_security, none_clarification_needed, none_unsupported, error_internal"},
            "links": {
                "type": "array", 
                "description": f"Optional list of links to related entities. Each link should have 'kind' ({', '.join(dev.LinkKind.__args__)}) and 'id' (entity identifier)", 
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "description": f"Type of entity (LinkKind): {', '.join(dev.LinkKind.__args__)}"},
                        "id": {"type": "string", "description": "ID of the entity"}
                    },
                    "required": ["kind", "id"]
                }, 
                "nullable": True
            }
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_ProvideAgentResponse
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, message: str, outcome: str, links: list = None) -> str:
        return self._execute_api_call(message=message, outcome=outcome, links=links or [])


class ListProjectsTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "list_projects"
        self.description = "List projects in the system. Required parameters: offset (int), limit (int)"
        self.inputs = {
            "offset": {"type": "integer", "description": "Pagination offset"},
            "limit": {"type": "integer", "description": "Maximum number of results to return, max value = 5"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_ListProjects
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int) -> str:
        return self._execute_api_call(offset=offset, limit=limit)


class ListEmployeesTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "list_employees"
        self.description = "List employees in the system. Required parameters: offset (int), limit (int)"
        self.inputs = {
            "offset": {"type": "integer", "description": "Pagination offset"},
            "limit": {"type": "integer", "description": "Maximum number of results to return"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_ListEmployees
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int) -> str:
        return self._execute_api_call(offset=offset, limit=limit)


class ListCustomersTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "list_customers"
        self.description = "List customers in the system. Required parameters: offset (int), limit (int)"
        self.inputs = {
            "offset": {"type": "integer", "description": "Pagination offset"},
            "limit": {"type": "integer", "description": "Maximum number of results to return, max value = 5"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_ListCustomers
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int) -> str:
        return self._execute_api_call(offset=offset, limit=limit)


class GetCustomerTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "get_customer"
        self.description = "Get details of a specific customer. Required parameter: id (str)"
        self.inputs = {
            "id": {"type": "string", "description": "ID of the customer to retrieve"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_GetCustomer
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, id: str) -> str:
        return self._execute_api_call(id=id)


class GetEmployeeTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "get_employee"
        self.description = "Get details of a specific employee. Required parameter: id (str)"
        self.inputs = {
            "id": {"type": "string", "description": "ID of the employee to retrieve"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_GetEmployee
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, id: str) -> str:
        return self._execute_api_call(id=id)


class GetProjectTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "get_project"
        self.description = "Get details of a specific project. Required parameter: id (str)"
        self.inputs = {
            "id": {"type": "string", "description": "ID of the project to retrieve"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_GetProject
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, id: str) -> str:
        return self._execute_api_call(id=id)


class GetTimeEntryTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "get_time_entry"
        self.description = "Get details of a specific time entry. Required parameter: id (str)"
        self.inputs = {
            "id": {"type": "string", "description": "ID of the time entry to retrieve"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_GetTimeEntry
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, id: str) -> str:
        return self._execute_api_call(id=id)


class SearchProjectsTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "search_projects"
        self.description = "Search for projects. Required parameters: offset (int), limit (int). Optional: query (str), customer_id (str), status (list), team (dict), include_archived (bool)"
        self.inputs = {
            "query": {"type": "string", "description": "Optional search query for project name or description", "nullable": True},
            "offset": {"type": "integer", "description": "Pagination offset"},
            "limit": {"type": "integer", "description": "Maximum number of results to return, max value = 5"},
            "customer_id": {"type": "string", "description": "Optional filter by customer ID", "nullable": True},
            "status": {"type": "array", "description": "Optional filter by status list (DealPhase): 'idea', 'exploring', 'active', 'paused', 'archived'", "nullable": True},
            "team": {"type": "object", "description": "Optional team filter (ProjectTeamFilter) with properties: employee_id (str), role (TeamRole: 'Lead', 'Engineer', 'Designer', 'QA', 'Ops', 'Other'), min_time_slice (float)", "nullable": True},
            "include_archived": {"type": "boolean", "description": "Include archived projects", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_SearchProjects
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int, query: str = None, customer_id: str = None, status: list = None, team: dict = None, include_archived: bool = False) -> str:
        return self._execute_api_call(query=query, offset=offset, limit=limit, customer_id=customer_id, status=status, team=team, include_archived=include_archived)


class SearchEmployeesTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "search_employees"
        self.description = "Search for employees. Required parameters: offset (int), limit (int). Optional: query (str), location (str), department (str), manager (str), skills (list), wills (list)"
        self.inputs = {
            "query": {"type": "string", "description": "Optional search query for employee name or email", "nullable": True},
            "offset": {"type": "integer", "description": "Pagination offset"},
            "limit": {"type": "integer", "description": "Maximum number of results to return, max value = 5"},
            "location": {"type": "string", "description": "Optional filter by location", "nullable": True},
            "department": {"type": "string", "description": "Optional filter by department", "nullable": True},
            "manager": {"type": "string", "description": "Optional filter by manager", "nullable": True},
            "skills": {"type": "array", "description": "Optional filter by skills (list of SkillFilter objects with properties: name (str), min_level (int), max_level (int, default 0))", "nullable": True},
            "wills": {"type": "array", "description": "Optional filter by wills (list of SkillFilter objects with properties: name (str), min_level (int), max_level (int, default 0))", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_SearchEmployees
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int, query: str = None, location: str = None, department: str = None, manager: str = None, skills: list = None, wills: list = None) -> str:
        return self._execute_api_call(query=query, offset=offset, limit=limit, location=location, department=department, manager=manager, skills=skills, wills=wills)


class LogTimeEntryTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "log_time_entry"
        self.description = "Log a new time entry. Required parameters: employee (str), date (str), hours (float), work_category (str), notes (str), billable (bool), status (str), logged_by (str). Optional: customer (str), project (str)"
        self.inputs = {
            "employee": {"type": "string", "description": "ID of the employee"},
            "customer": {"type": "string", "description": "Optional ID of the customer", "nullable": True},
            "project": {"type": "string", "description": "Optional ID of the project", "nullable": True},
            "date": {"type": "string", "description": "Date of the work (YYYY-MM-DD format)"},
            "hours": {"type": "number", "description": "Number of hours worked"},
            "work_category": {"type": "string", "description": "Category of work performed"},
            "notes": {"type": "string", "description": "Notes about the work performed"},
            "billable": {"type": "boolean", "description": "Whether the time is billable"},
            "status": {"type": "string", "description": "Status (TimeEntryStatus): '', 'draft', 'submitted', 'approved', 'invoiced', 'voided'"},
            "logged_by": {"type": "string", "description": "ID of the employee logging the entry"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_LogTimeEntry
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, employee: str, date: str, hours: float, work_category: str, notes: str, billable: bool, status: str, logged_by: str, customer: str = None, project: str = None) -> str:
        return self._execute_api_call(employee=employee, customer=customer, project=project, date=date, hours=hours, work_category=work_category, notes=notes, billable=billable, status=status, logged_by=logged_by)


class SearchTimeEntriesTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "search_time_entries"
        self.description = "Search for time entries. Required parameters: offset (int), limit (int). Optional: employee (str), customer (str), project (str), date_from (str), date_to (str), work_category (str), billable (str), status (str)"
        self.inputs = {
            "employee": {"type": "string", "description": "Optional filter by employee ID", "nullable": True},
            "customer": {"type": "string", "description": "Optional filter by customer ID", "nullable": True},
            "project": {"type": "string", "description": "Optional filter by project ID", "nullable": True},
            "date_from": {"type": "string", "description": "Optional start date filter (YYYY-MM-DD)", "nullable": True},
            "date_to": {"type": "string", "description": "Optional end date filter (YYYY-MM-DD)", "nullable": True},
            "work_category": {"type": "string", "description": "Optional filter by work category", "nullable": True},
            "billable": {"type": "string", "description": "Optional filter (BillableFilter): '', 'billable', 'non_billable'", "nullable": True},
            "status": {"type": "string", "description": "Optional filter by status (TimeEntryStatus): '', 'draft', 'submitted', 'approved', 'invoiced', 'voided'", "nullable": True},
            "offset": {"type": "integer", "description": "Pagination offset"},
            "limit": {"type": "integer", "description": "Maximum number of results to return, max value = 5"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_SearchTimeEntries
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int, employee: str = None, customer: str = None, project: str = None, date_from: str = None, date_to: str = None, work_category: str = None, billable: str = "", status: str = "") -> str:
        return self._execute_api_call(employee=employee, customer=customer, project=project, date_from=date_from, date_to=date_to, work_category=work_category, billable=billable, status=status, offset=offset, limit=limit)


class SearchCustomersTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "search_customers"
        self.description = "Search for customers. Required parameters: offset (int), limit (int). Optional: query (str), deal_phase (list), account_managers (list), locations (list)"
        self.inputs = {
            "query": {"type": "string", "description": "Optional search query for customer name", "nullable": True},
            "deal_phase": {"type": "array", "description": "Optional filter by deal phase list (DealPhase): 'idea', 'exploring', 'active', 'paused', 'archived'", "nullable": True},
            "account_managers": {"type": "array", "description": "Optional filter by account manager IDs", "nullable": True},
            "locations": {"type": "array", "description": "Optional filter by locations", "nullable": True},
            "offset": {"type": "integer", "description": "Pagination offset"},
            "limit": {"type": "integer", "description": "Maximum number of results to return, max value = 5"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_SearchCustomers
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int, query: str = None, deal_phase: list = None, account_managers: list = None, locations: list = None) -> str:
        return self._execute_api_call(query=query, deal_phase=deal_phase, account_managers=account_managers, locations=locations, offset=offset, limit=limit)


class UpdateTimeEntryTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "update_time_entry"
        self.description = "Update an existing time entry. Required parameters: id (str), date (str), hours (float), work_category (str), notes (str), billable (bool), status (str), changed_by (str)"
        self.inputs = {
            "id": {"type": "string", "description": "ID of the time entry to update"},
            "date": {"type": "string", "description": "Date of the work (YYYY-MM-DD format)"},
            "hours": {"type": "number", "description": "Updated number of hours"},
            "work_category": {"type": "string", "description": "Updated work category"},
            "notes": {"type": "string", "description": "Updated notes"},
            "billable": {"type": "boolean", "description": "Whether the time is billable"},
            "status": {"type": "string", "description": "Updated status (TimeEntryStatus): '', 'draft', 'submitted', 'approved', 'invoiced', 'voided'"},
            "changed_by": {"type": "string", "description": "ID of the employee making the change"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_UpdateTimeEntry
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, id: str, date: str, hours: float, work_category: str, notes: str, billable: bool, status: str, changed_by: str) -> str:
        return self._execute_api_call(id=id, date=date, hours=hours, work_category=work_category, notes=notes, billable=billable, status=status, changed_by=changed_by)


class UpdateProjectTeamTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "update_project_team"
        self.description = "Update the team members assigned to a project. Required parameters: id (str), team (list of Workload objects). Optional: changed_by (str)"
        self.inputs = {
            "id": {"type": "string", "description": "ID of the project"},
            "team": {"type": "array", "description": "List of Workload objects with properties: employee (str, employee ID), time_slice (float), role (TeamRole: 'Lead', 'Engineer', 'Designer', 'QA', 'Ops', 'Other')"},
            "changed_by": {"type": "string", "description": "Optional ID of the employee making the change", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_UpdateProjectTeam
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, id: str, team: list, changed_by: str = None) -> str:
        return self._execute_api_call(id=id, team=team, changed_by=changed_by)


class UpdateProjectStatusTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "update_project_status"
        self.description = "Update the status of a project. Required parameters: id (str), status (str). Optional: changed_by (str)"
        self.inputs = {
            "id": {"type": "string", "description": "ID of the project"},
            "status": {"type": "string", "description": "New status (DealPhase): 'idea', 'exploring', 'active', 'paused', 'archived'"},
            "changed_by": {"type": "string", "description": "Optional ID of the employee making the change", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_UpdateProjectStatus
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, id: str, status: str, changed_by: str = None) -> str:
        return self._execute_api_call(id=id, status=status, changed_by=changed_by)


class UpdateEmployeeInfoTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "update_employee_info"
        self.description = "Update employee information. Required parameter: employee (str). Optional: notes (str), salary (int), skills (list), wills (list), location (str), department (str), changed_by (str)"
        self.inputs = {
            "employee": {"type": "string", "description": "ID of the employee"},
            "notes": {"type": "string", "description": "Optional updated notes", "nullable": True},
            "salary": {"type": "integer", "description": "Optional updated salary", "nullable": True},
            "skills": {"type": "array", "description": "Optional list of SkillLevel objects with properties: name (str), level (int)", "nullable": True},
            "wills": {"type": "array", "description": "Optional list of SkillLevel objects for wills with properties: name (str), level (int)", "nullable": True},
            "location": {"type": "string", "description": "Optional updated location", "nullable": True},
            "department": {"type": "string", "description": "Optional updated department", "nullable": True},
            "changed_by": {"type": "string", "description": "Optional ID of employee making the change", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_UpdateEmployeeInfo
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, employee: str, notes: str = None, salary: int = None, skills: list = None, wills: list = None, location: str = None, department: str = None, changed_by: str = None) -> str:
        return self._execute_api_call(employee=employee, notes=notes, salary=salary, skills=skills, wills=wills, location=location, department=department, changed_by=changed_by)


class TimeSummaryByProjectTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "time_summary_by_project"
        self.description = "Get time summary by project. Required parameters: date_from (str), date_to (str). Optional: customers (list), projects (list), employees (list), billable (str)"
        self.inputs = {
            "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            "customers": {"type": "array", "description": "Optional list of customer IDs to filter", "nullable": True},
            "projects": {"type": "array", "description": "Optional list of project IDs to filter", "nullable": True},
            "employees": {"type": "array", "description": "Optional list of employee IDs to filter", "nullable": True},
            "billable": {"type": "string", "description": "Optional filter (BillableFilter): '', 'billable', 'non_billable'", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_TimeSummaryByProject
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, date_from: str, date_to: str, customers: list = None, projects: list = None, employees: list = None, billable: str = "") -> str:
        return self._execute_api_call(date_from=date_from, date_to=date_to, customers=customers, projects=projects, employees=employees, billable=billable)


class TimeSummaryByEmployeeTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "time_summary_by_employee"
        self.description = "Get time summary by employee. Required parameters: date_from (str), date_to (str). Optional: customers (list), projects (list), employees (list), billable (str)"
        self.inputs = {
            "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            "customers": {"type": "array", "description": "Optional list of customer IDs to filter", "nullable": True},
            "projects": {"type": "array", "description": "Optional list of project IDs to filter", "nullable": True},
            "employees": {"type": "array", "description": "Optional list of employee IDs to filter", "nullable": True},
            "billable": {"type": "string", "description": "Optional filter (BillableFilter): '', 'billable', 'non_billable'", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_TimeSummaryByEmployee
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, date_from: str, date_to: str, customers: list = None, projects: list = None, employees: list = None, billable: str = "") -> str:
        return self._execute_api_call(date_from=date_from, date_to=date_to, customers=customers, projects=projects, employees=employees, billable=billable)


class ListWikiTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "list_wiki"
        self.description = "List all wiki articles in the system. No required parameters."
        self.inputs = {}
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_ListWiki
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self) -> str:
        return self._execute_api_call()


class LoadWikiTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "load_wiki"
        self.description = "Load a specific wiki article. Required parameter: file (str)"
        self.inputs = {
            "file": {"type": "string", "description": "Path to the wiki file to load"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_LoadWiki
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, file: str) -> str:
        return self._execute_api_call(file=file)


class SearchWikiTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "search_wiki"
        self.description = "Search wiki articles using a regex pattern. Required parameter: query_regex (str)"
        self.inputs = {
            "query_regex": {"type": "string", "description": "Regex pattern to search for in wiki content"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_SearchWiki
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, query_regex: str) -> str:
        return self._execute_api_call(query_regex=query_regex)


class UpdateWikiTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "update_wiki"
        self.description = "Update a wiki article. Required parameters: file (str), content (str). Optional: changed_by (str)"
        self.inputs = {
            "file": {"type": "string", "description": "Path to the wiki file to update"},
            "content": {"type": "string", "description": "New content for the wiki article"},
            "changed_by": {"type": "string", "description": "Optional ID of employee making the change", "nullable": True}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_UpdateWiki
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, file: str, content: str, changed_by: str = None) -> str:
        return self._execute_api_call(file=file, content=content, changed_by=changed_by)


class WhoAmITool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "who_am_i"
        self.description = "Get information about the current user, location, department, today's date, and wiki version. No parameters required."
        self.inputs = {}
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = dev.Req_WhoAmI
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self) -> str:
        return self._execute_api_call()


class FinalAnswerTool(Tool):
    """Tool for providing final task completion summary"""

    def __init__(self):
        self.name = "final_answer"
        self.description = "Provide a final summary when the task is completed or if it is not possible to complete it after reviewing all rules and ensuring full compliance. Required parameter: answer (str)"
        self.inputs = {
            "answer": {
                "type": "string",
                "description": "The final answer to return.",
            }
        }
        self.output_type = "string"
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, answer: str) -> str:
        logging.info(f"{CLI_GREEN}[FINAL]{CLI_CLR} Task completed: {answer}")

        return answer
