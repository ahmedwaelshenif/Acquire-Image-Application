using System;
using System.Collections.Generic;
using System.Text;
using System.ComponentModel.DataAnnotations;
namespace Domain.Entities
{
    
    public class Member
    {
        [Key]
        public int Id { get; set; }

        [Required]
        public string FullName { get; set; }

        [Required]
        [EmailAddress]
        public string Email { get; set; }

        [Required]
        [Range(1, 4)]
        public int AcademicYear { get; set; }

        [Required]
        public byte[] FaceImage { get; set; }
        [Required]
        public byte[] IdImage { get; set; }
        [Required]
        public byte[] EmbeddingData { get; set; }

    }
}
