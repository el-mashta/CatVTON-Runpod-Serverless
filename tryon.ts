export async function runVTON(
  person: File,
  cloth: File,
  description: string
): Promise<string> {
  const formData = new FormData();
  formData.append("person", person);
  formData.append("cloth", cloth);
  formData.append("garment_des", description);

  // Use ingress routing to backend API
  const response = await fetch("/api/tryon", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error(
      "VTON API request failed with status:",
      response.status,
      "and message:",
      errorText
    );
    throw new Error(`Try-on request failed: ${errorText}`);
  }

  const data = await response.json();
  console.log("Full response from /api/tryon:", JSON.stringify(data, null, 2));
  return data.output;
}
