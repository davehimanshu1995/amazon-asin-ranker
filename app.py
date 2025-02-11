import os
from flask import Flask, request, render_template, send_file
import pandas as pd

app = Flask(__name__, template_folder="templates")

# Create "uploads" folder dynamically (Render does not allow persistent storage)
UPLOAD_FOLDER = "/tmp/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "❌ No file uploaded!", 400  # Return error message

        file = request.files["file"]
        if file.filename == "":
            return "❌ No selected file!", 400

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)  # Save file temporarily in /tmp/uploads

        try:
            # Read Excel file (Ensure openpyxl is installed)
            df = pd.read_excel(file_path, engine="openpyxl")  

            # Check if required columns exist
            if 'ASIN' not in df.columns or 'Ranking' not in df.columns:
                return "❌ Missing 'ASIN' or 'Ranking' column!", 400

            # Extract ASINs and Rankings
            asin_data = df[['ASIN', 'Ranking']]

            # Show extracted data (you can process it further as needed)
            return render_template("index.html", table_data=asin_data.to_html(), message="✅ File uploaded successfully!")

        except Exception as e:
            return f"❌ Error processing file: {str(e)}", 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
