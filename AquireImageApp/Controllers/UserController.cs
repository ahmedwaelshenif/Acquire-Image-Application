using Microsoft.AspNetCore.Mvc;
namespace AcquireImageApp.Controllers
{
    [ApiController]
    public class UserController : Controller
    {
        private readonly HttpClient httpClient;

        public UserController(HttpClient httpClient)
        {
            this.httpClient = httpClient;
        }

        [HttpPost("/CheckImg")]
        [Consumes("multipart/form-data")]
        public async Task<IActionResult> CheckImg(IFormFile image)
        {
            if (image == null || image.Length == 0)
                return BadRequest("No image uploaded.");

            using var memoryStream = new MemoryStream();

            await image.CopyToAsync(memoryStream);

            byte[] imageBytes = memoryStream.ToArray();

            string base64Image = Convert.ToBase64String(imageBytes);

            var payload = new
            {
                image = base64Image
            };

            using var response = await httpClient.PostAsJsonAsync( "http://localhost:8000/api/verify", payload );

            var responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                return StatusCode(
                    (int)response.StatusCode,
                    responseBody
                );
            }

            return Content(responseBody, "application/json");
        }
    }
}
    

