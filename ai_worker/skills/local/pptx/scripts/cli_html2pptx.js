const pptxgen = require('pptxgenjs');
const html2pptx = require('./html2pptx');
const path = require('path');

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node cli_html2pptx.js <html_file> <output_file>");
    process.exit(1);
  }

  const htmlFile = args[0];
  const outputFile = args[1];

  try {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9'; // Default layout

    console.log(`Converting ${htmlFile} to PPTX...`);
    
    // Call html2pptx
    // Note: html2pptx expects htmlFile path
    await html2pptx(htmlFile, pptx);

    // Write file
    await pptx.writeFile({ fileName: outputFile });
    console.log(`Presentation saved to ${outputFile}`);
  } catch (error) {
    console.error("Error:", error);
    process.exit(1);
  }
}

main();
