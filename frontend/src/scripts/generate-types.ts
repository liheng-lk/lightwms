import openapiTS, { astToString } from 'openapi-typescript';
import fs from 'fs/promises';
import path from 'path';

async function generateTypes() {
  const schemaPath = path.join(process.cwd(), 'src/schemas/openapi.json');
  const outputPath = path.join(process.cwd(), 'src/lib/types/generated/api.ts');
  
  // 检查 schema 文件是否存在
  try {
    await fs.access(schemaPath);
  } catch {
    console.error(`Schema file not found: ${schemaPath}`);
    console.log('Run "npm run fetch-schema" first to download the schema.');
    
    // 允许跳过（CI/CD 场景）
    if (process.env.ALLOW_SCHEMA_FAIL === '1') {
      // 检查类型文件是否已存在
      try {
        await fs.access(outputPath);
        console.log('ALLOW_SCHEMA_FAIL=1, keeping existing types file.');
        process.exit(0);
      } catch {
        // 文件不存在，创建占位符
        console.log('ALLOW_SCHEMA_FAIL=1, creating placeholder types.');
        await fs.mkdir(path.dirname(outputPath), { recursive: true });
        await fs.writeFile(outputPath, '// Placeholder - run fetch-schema and generate-types to populate\nexport {};\n');
        process.exit(0);
      }
    }
    process.exit(1);
  }
  
  console.log(`Generating types from ${schemaPath}...`);
  
  const schema = JSON.parse(await fs.readFile(schemaPath, 'utf-8'));
  const ast = await openapiTS(schema);
  const output = astToString(ast);
  
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, output);
  
  console.log(`Types generated at ${outputPath}`);
}

generateTypes().catch((error) => {
  console.error('Type generation failed:', error);
  process.exit(1);
});
