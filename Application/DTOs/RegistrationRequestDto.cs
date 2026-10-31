using Domain.Enums;
using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Text;
using Microsoft.AspNetCore.Http;

namespace Application.DTOs
{
    public class RegistrationRequestDto
    {

        [Required]
        public int MemberId { get; set; }

        [Required]
        public string FullName { get; set; }

        [Required]
        [EmailAddress]
        public string Email { get; set; }

        [Required]
        public IFormFile FaceImage { get; set; }

        [Required]
        public IFormFile  IdImage { get; set; }


        [Required]
        [Range(1, 4)]
        public int AcademicYear { get; set; }

    }
}
