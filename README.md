# PROJECT KARLA

**Project Karla** is an automated, multi-agent pipeline designed to transform natural language prompts into fully functional [Ren’Py](https://www.renpy.org/) visual novel games. By leveraging specialized LLM agents, the latest agentic orchestration frameworks,  and a dedicated build layer, Karla handles everything from narrative structure and character development to asset generation and final script compilation.

---

## 🏗️ System Architecture

Project Karla is divided into four primary layers to ensure a modular and scalable development process.

### 1. Discovery Layer (Frontend)
*Status: Backlog*

A browser-based (HTML/CSS/JavaScript) interface designed to guide the user through initial creative choices (genre, tone, etc.), setting the "seed" for the generation process.

### 2. Creative Layer (Agent Orchestration)
*Status: In Progress*

The heart of the project, where high-level concepts are expanded into game-ready content through specialized agents:

* **Narrative Agent (The Director):** Processes user input into a structured 3-act story. It outputs a high-level JSON outline defining the plot, characters, and scene summaries.
* **Dialogue Agent:** Consumes the narrative JSON to write comprehensive dialogue, monologues, and narration in Ren’Py-compatible formats.
* **Visual Agent:** Parses character and setting descriptions to generate background art and character portrait textures (via SD/Midjourney).
* **Staging Agent (The Compiler):** Acts as the final creative gatekeeper. It maps generated assets to dialogue blocks and ensures all file paths and IDs align with the project's technical requirements.

### 3. Build Layer (Automation)
*Status: In Progress*

Creates a playable Ren'Py game from the **Staging Manifest**
* **Skeletal Initialization:** A PowerShell-based automation tool that scaffolds a linted, project-ready Ren’Py directory.
* **Script Injection:** A Python/PowerShell processor that takes the **Staging Manifest** and injects the logic into `.rpy` files while moving assets into the correct game directories.

### 4. Runtime Layer
*Status: InProgress*

* **Ren’Py:** The open-source Ren'Py engine itself. The final executable environment where the generated assets and scripts are executed.

---

## 🔄 Multi-Agent Pipeline Overview

The following table outlines the flow of data through the system:

| Phase | Agent / Component | Responsibility | Input $\rightarrow$ Output |
| :--- | :--- | :--- | :--- |
| **Discovery** | **Discovery Agent** | Gathers user rquirements and input | User choices $\rightarrow$ Schematized System Prompt |
| **Creative** | **Narrative Agent** | Generates the 3-act structural JSON. | System Prompt $\rightarrow$ High-level JSON Game Spec |
| **Creative** | **Dialogue Agent** | Expands summaries into full dialogue blocks. | JSON Game Spec $\rightarrow$ Script Fragments |
| **Creative** | **Visual Agent** | Generates BGs and Sprites from descriptions. | JSON Game Spec $\rightarrow$ Character & Environment Art Assets |
| **Creative** | **Staging Agent** | Maps assets to dialogue; validates file paths. | All above $\rightarrow$ Standardized Manifest |
| **Build** | **PowerShell/Python** | Injects manifest into `.rpy`; organizes files. | Manifest $\rightarrow$ Ren'Py Build Files |
| **Runtime** | **Ren'Py** | Presents the finished game to the user | `.rpy` & supporting RP files $\rightarrow$ Executable Game |
