import fs from 'fs/promises';
import path from 'path';

const SCHEMA_URL = process.env.BACKEND_URL 
  ? `${process.env.BACKEND_URL}/api/schema/`
  : 'http://localhost:8000/api/schema/';

async function fetchSchema() {
  console.log(`Fetching schema from ${SCHEMA_URL}...`);
  
  try {
    const response = await fetch(SCHEMA_URL);
    if (!response.ok) {
      throw new Error(`Failed to fetch schema: ${response.status}`);
    }
    
    const schema = await response.json();
    const outputPath = path.join(process.cwd(), 'src/schemas/openapi.json');
    
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.writeFile(outputPath, JSON.stringify(schema, null, 2));
    
    console.log(`Schema saved to ${outputPath}`);
  } catch (error) {
    console.error('Failed to fetch schema:', error);
    console.log('Make sure the backend is running and accessible.');
    process.exit(1);
  }
}

fetchSchema();
