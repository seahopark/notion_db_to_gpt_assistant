import os
from dotenv import load_dotenv
from notion_client import Client
from openai import OpenAI
import tempfile
import shutil

# Load environment variables
load_dotenv()

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_TOKEN"))

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_page_blocks(page_id):
    """Fetch all blocks from a Notion page"""
    try:
        blocks = []
        has_more = True
        start_cursor = None
        
        while has_more:
            response = notion.blocks.children.list(
                block_id=page_id,
                start_cursor=start_cursor
            )
            
            blocks.extend(response["results"])
            has_more = response["has_more"]
            start_cursor = response.get("next_cursor")
        
        return blocks
    except Exception as e:
        print(f"Error fetching page blocks: {str(e)}")
        return None

def block_to_markdown(block):
    """Convert a Notion block to Markdown format"""
    if block["type"] == "paragraph":
        text = "".join([text["plain_text"] for text in block["paragraph"]["rich_text"]])
        return text + "\n\n"
    elif block["type"] == "heading_1":
        text = "".join([text["plain_text"] for text in block["heading_1"]["rich_text"]])
        return f"# {text}\n\n"
    elif block["type"] == "heading_2":
        text = "".join([text["plain_text"] for text in block["heading_2"]["rich_text"]])
        return f"## {text}\n\n"
    elif block["type"] == "heading_3":
        text = "".join([text["plain_text"] for text in block["heading_3"]["rich_text"]])
        return f"### {text}\n\n"
    elif block["type"] == "bulleted_list_item":
        text = "".join([text["plain_text"] for text in block["bulleted_list_item"]["rich_text"]])
        return f"- {text}\n"
    elif block["type"] == "numbered_list_item":
        text = "".join([text["plain_text"] for text in block["numbered_list_item"]["rich_text"]])
        return f"1. {text}\n"
    elif block["type"] == "to_do":
        text = "".join([text["plain_text"] for text in block["to_do"]["rich_text"]])
        checked = "x" if block["to_do"]["checked"] else " "
        return f"- [{checked}] {text}\n"
    elif block["type"] == "code":
        text = "".join([text["plain_text"] for text in block["code"]["rich_text"]])
        language = block["code"]["language"]
        return f"```{language}\n{text}\n```\n\n"
    elif block["type"] == "quote":
        text = "".join([text["plain_text"] for text in block["quote"]["rich_text"]])
        return f"> {text}\n\n"
    elif block["type"] == "callout":
        text = "".join([text["plain_text"] for text in block["callout"]["rich_text"]])
        color = block["callout"]["color"]
        return f"> [!{color}]\n> {text}\n\n"
    return ""

def get_database_content():
    """Fetch content from Notion database"""
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    try:
        # Query the database
        response = notion.databases.query(
            database_id=database_id,
            page_size=100  # Adjust as needed
        )
        
        # Process the results
        database_content = []
        for page in response["results"]:
            # Extract properties from the page
            properties = page["properties"]
            # You can customize this part based on your database structure
            row_data = {}
            for prop_name, prop_data in properties.items():
                if prop_data["type"] == "title":
                    row_data[prop_name] = prop_data["title"][0]["plain_text"] if prop_data["title"] else ""
                elif prop_data["type"] == "rich_text":
                    row_data[prop_name] = prop_data["rich_text"][0]["plain_text"] if prop_data["rich_text"] else ""
                elif prop_data["type"] == "select":
                    row_data[prop_name] = prop_data["select"]["name"] if prop_data["select"] else ""
            
            # Get page blocks
            blocks = get_page_blocks(page["id"])
            if blocks:
                row_data["content"] = "".join([block_to_markdown(block) for block in blocks])
            
            database_content.append(row_data)
        
        return database_content
    
    except Exception as e:
        print(f"Error fetching database content: {str(e)}")
        return None

def get_existing_assistant():
    """Get the existing assistant"""
    try:
        assistant_id = os.getenv("ASSISTANT_ID")
        if not assistant_id:
            print("Error: ASSISTANT_ID not found in .env file")
            return None
            
        assistant = client.beta.assistants.retrieve(assistant_id)
        print(f"Successfully retrieved assistant: {assistant.name}")
        return assistant
    
    except Exception as e:
        print(f"Error retrieving assistant: {str(e)}")
        return None

def create_markdown_file(content):
    """Create a Markdown file with the database content"""
    try:
        # Get the title from the first content item
        title = "Notion_Database"
        if content and len(content) > 0:
            # Find the title property (usually the first property)
            for prop_name, prop_value in content[0].items():
                if prop_value and prop_name != "content":  # Skip content field
                    title = prop_value
                    break
        
        # Create a safe filename from the title
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        
        # Create a temporary file with markdown extension
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'_{safe_title}.md', encoding='utf-8') as temp_file:
            # Write title
            temp_file.write(f"# {title}\n\n")
            
            # Write content
            if content:
                # First write the page content if available
                for item in content:
                    if "content" in item and item["content"]:
                        temp_file.write(item["content"])
                        temp_file.write("\n---\n\n")  # Add separator between pages
                
                # Then write the database properties as a table
                temp_file.write("## Database Properties\n\n")
                # Get headers from the first item (excluding content)
                headers = [h for h in content[0].keys() if h != "content"]
                
                # Write table header
                temp_file.write("| " + " | ".join(headers) + " |\n")
                temp_file.write("| " + " | ".join(["---" for _ in headers]) + " |\n")
                
                # Write data rows
                for item in content:
                    row = [str(item.get(header, '')) for header in headers]
                    temp_file.write("| " + " | ".join(row) + " |\n")
            
            return temp_file.name
            
    except Exception as e:
        print(f"Error creating Markdown file: {str(e)}")
        return None

def upload_file_to_assistant(file_path, assistant_id):
    """Upload a file and attach it to the assistant"""
    try:
        # Upload the new file
        with open(file_path, "rb") as file:
            file_response = client.files.create(
                file=file,
                purpose="assistants"
            )
        
        # Get the file ID
        file_id = file_response.id
        
        # Create a new assistant with the file
        new_assistant = client.beta.assistants.create(
            name="Antony 문서 작성 봇",  # 기존 Assistant의 이름을 유지
            instructions="You are an assistant that helps users understand and work with the Notion database content.",
            model="gpt-4-turbo-preview",
            tools=[{"type": "file_search"}],
            metadata={"file_id": file_id}
        )
        
        print(f"Successfully created new assistant with file: {file_id}")
        return new_assistant
    
    except Exception as e:
        print(f"Error uploading file to assistant: {str(e)}")
        return None

def save_file_locally(temp_file_path, title):
    """Save the file to a local directory"""
    try:
        # Create a directory for files if it doesn't exist
        output_dir = "notion_files"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create a safe filename from the title
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        
        # Get the file extension from the temp file
        _, ext = os.path.splitext(temp_file_path)
        
        # Create the destination file path
        dest_file_path = os.path.join(output_dir, f"{safe_title}{ext}")
        
        # Copy the temporary file to the destination
        shutil.copy2(temp_file_path, dest_file_path)
        print(f"File saved locally at: {dest_file_path}")
        return dest_file_path
    except Exception as e:
        print(f"Error saving file locally: {str(e)}")
        return None

def main():
    # Get database content
    database_content = get_database_content()
    
    if database_content:
        # Get existing assistant
        assistant = get_existing_assistant()
        
        if assistant:
            print(f"Using existing assistant with ID: {assistant.id}")
            
            # Create a Markdown file with the database content
            md_file_path = create_markdown_file(database_content)
            
            if md_file_path:
                try:
                    # Get the title from the first content item
                    title = "Notion_Database"
                    if database_content and len(database_content) > 0:
                        for prop_name, prop_value in database_content[0].items():
                            if prop_value:
                                title = prop_value
                                break
                    
                    # Save file locally
                    local_file_path = save_file_locally(md_file_path, title)
                    
                    # Create a new assistant with the updated file
                    new_assistant = upload_file_to_assistant(md_file_path, assistant.id)
                    if new_assistant:
                        print(f"New assistant created with ID: {new_assistant.id}")
                        # Update .env file with new assistant ID
                        with open('.env', 'r') as file:
                            env_content = file.read()
                        with open('.env', 'w') as file:
                            file.write(env_content.replace(
                                f"ASSISTANT_ID={assistant.id}",
                                f"ASSISTANT_ID={new_assistant.id}"
                            ))
                        print("Updated .env file with new assistant ID")
                finally:
                    # Clean up the temporary file
                    os.unlink(md_file_path)
            else:
                print("Failed to create Markdown file with database content")
        else:
            print("Failed to retrieve assistant")
    else:
        print("Failed to fetch database content")

if __name__ == "__main__":
    main() 